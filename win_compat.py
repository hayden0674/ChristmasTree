import sys

if sys.platform == "win32":
    import ctypes
    import pygame

    # 1. 把物理键盘按键直接映射为标准快捷键，无视中文输入法拦截
    _KEY_MAP = {}
    for _ch in "abcdefghijklmnopqrstuvwxyz0123456789":
        _scan = getattr(pygame, f"KSCAN_{_ch.upper()}", None)
        _code = getattr(pygame, f"K_{_ch}", None)
        if _scan is not None and _code is not None:
            _KEY_MAP[_scan] = _code

    for _name in ("SPACE", "ESCAPE", "RETURN", "LEFT", "RIGHT", "UP", "DOWN"):
        _scan = getattr(pygame, f"KSCAN_{_name}", None)
        _code = getattr(pygame, f"K_{_name}", None)
        if _scan is not None and _code is not None:
            _KEY_MAP[_scan] = _code

    def _fix_event(ev):
        if ev.type in (pygame.KEYDOWN, pygame.KEYUP):
            if getattr(ev, "key", 0) in (0, getattr(pygame, "K_UNKNOWN", 0)):
                mapped = _KEY_MAP.get(getattr(ev, "scancode", 0))
                if mapped:
                    return pygame.event.Event(
                        ev.type,
                        key=mapped,
                        mod=getattr(ev, "mod", 0),
                        scancode=getattr(ev, "scancode", 0),
                        unicode=getattr(ev, "unicode", ""),
                    )
        return ev

    _orig_get = pygame.event.get
    def _win_get(*args, **kwargs):
        return [_fix_event(e) for e in _orig_get(*args, **kwargs)]
    pygame.event.get = _win_get

    _orig_poll = pygame.event.poll
    def _win_poll():
        return _fix_event(_orig_poll())
    pygame.event.poll = _win_poll

    # 2. 启动窗口时自动关闭中文输入法并抢占键盘焦点
    _orig_set_mode = pygame.display.set_mode
    def _win_set_mode(*args, **kwargs):
        surf = _orig_set_mode(*args, **kwargs)
        try:
            pygame.key.stop_text_input()
            hwnd = pygame.display.get_wm_info().get("window")
            if hwnd:
                ctypes.windll.imm32.ImmAssociateContext(hwnd, 0)
                ctypes.windll.user32.ShowWindow(hwnd, 9)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                ctypes.windll.user32.SetFocus(hwnd)
        except Exception:
            pass
        return surf
    pygame.display.set_mode = _win_set_mode

    # 3. 按 P 选照片时暂时收起全屏窗口，防止选图对话框被挡在背后
    try:
        import tkinter as _tk
        import tkinter.filedialog as _fd

        def _wrap_dialog(orig_fn):
            def _wrapped(*args, **kwargs):
                hwnd = None
                was_fullscreen = False
                try:
                    screen = pygame.display.get_surface()
                    hwnd = pygame.display.get_wm_info().get("window")
                    if screen is not None and (screen.get_flags() & pygame.FULLSCREEN):
                        was_fullscreen = True
                        pygame.display.iconify()
                except Exception:
                    pass

                root = None
                try:
                    if kwargs.get("parent") is None:
                        root = _tk.Tk()
                        root.withdraw()
                        root.attributes("-topmost", True)
                        kwargs["parent"] = root
                    return orig_fn(*args, **kwargs)
                finally:
                    if root is not None:
                        try:
                            root.destroy()
                        except Exception:
                            pass
                    if hwnd:
                        try:
                            if was_fullscreen:
                                ctypes.windll.user32.ShowWindow(hwnd, 9)
                            ctypes.windll.user32.SetForegroundWindow(hwnd)
                            ctypes.windll.user32.SetFocus(hwnd)
                        except Exception:
                            pass
            return _wrapped

        _fd.askopenfilenames = _wrap_dialog(_fd.askopenfilenames)
        _fd.askopenfilename = _wrap_dialog(_fd.askopenfilename)
    except Exception:
        pass
