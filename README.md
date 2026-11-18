# 3D Gesture-Interactive Particle Christmas Tree (3D 手势交互粒子圣诞树)

[中文使用说明](#中文使用说明) | [English Guide](#english-guide)

---

## 中文使用说明

这是一个基于 Python、Pygame、OpenCV 和 MediaPipe 打造的 **3D 手势交互粒子圣诞树**。**零基础用户无需安装 Python 或配置任何代码环境，下载对应系统的安装包解压双击即可运行！**

### 1. 分系统下载渠道（零基础直链）

#### 🪟 Windows 系统下载渠道
- **直接下载地址**：[点击下载 Windows 版 (ChristmasTree-Windows.zip)](https://github.com/hayden0674/ChristmasTree/releases/latest/download/ChristmasTree-Windows.zip)
- **备用发布页**：[前往 GitHub Releases 页面下载](https://github.com/hayden0674/ChristmasTree/releases)
- **运行方法**：
  1. 下载后**右键解压**压缩包，双击运行里面的 `ParticleChristmasTree.exe`。
  2. 若弹出 Windows 蓝色安全保护提示，点击 **「更多信息」** → 再点击 **「仍要运行」** 即可。

#### 🍎 macOS（苹果电脑）下载渠道
- **直接下载地址**：[点击下载 macOS 版 (ChristmasTree-macOS.zip)](https://github.com/hayden0674/ChristmasTree/releases/latest/download/ChristmasTree-macOS.zip)
- **备用发布页**：[前往 GitHub Releases 页面下载](https://github.com/hayden0674/ChristmasTree/releases)
- **运行方法**：
  1. 下载后双击解压，运行 `ParticleChristmasTree.app`（首次打开请允许访问摄像头）。
  2. 若提示“无法验证开发者”，在图标上 **按住 Control 键点击（或右键）→ 选择「打开」** 即可正常启动。

### 2. 如何添加自己的照片（支持 1～100 张）

添加照片后，拍立得相框会直接挂满圣诞树表面，并自动触发 **6 朵连环烟花与星光迸发特效**：
- **方法一（最快捷）**：打开圣诞树后直接按键盘 **`P` 键**，在弹出的系统窗口中多选电脑里的照片点击确定即可。
- **方法二（文件夹热加载）**：首次运行程序会自动在电脑桌面生成 **`圣诞树照片库`** 文件夹，直接把照片（支持 `.jpg` / `.png` / `.webp` / `.heic`）拖进去，1 秒内自动挂上圣诞树，无需重启；想删照片直接去该文件夹删除即可。

### 3. 隔空手势与快捷键说明
- **张开五指 (Open Palm)**：圣诞树散开成 3D 星海（手离摄像头越近星海越聚拢，越远越开阔）。
- **张开手掌捏合 (Open Palm + Pinch)**：保持中指、无名指、小指张开的同时捏合拇指与食指，粒子保持 **3D 星海散开状态**并抓取放大一张照片。
- **握拳捏合 (Fist + Pinch)**：保持中指、无名指、小指握拳收拢的同时捏合拇指与食指，粒子保持 **圣诞树聚合状态**并在树前抓取放大一张照片。
- **握拳 (Fist)**：所有星光与照片重新聚合成圣诞树。
- **快捷键**：`P` 添加照片 | `Space` 切换 3 套主题 | `F` 放烟花 | `R` 重播开场 | `Tab` 切换全屏/窗口 | `V` 摄像头调试窗 | `ESC` 退出。

---

## English Guide

An interactive **3D Particle Christmas Tree** controlled by real-time hand gestures (built with Python, Pygame, OpenCV, and MediaPipe). **No Python installation or coding setup required!**

### 1. Download Channels (Windows & macOS)

#### 🪟 Windows Download
- **Direct Download**: [Download ChristmasTree-Windows.zip](https://github.com/hayden0674/ChristmasTree/releases/latest/download/ChristmasTree-Windows.zip)
- **Release Page**: [GitHub Releases](https://github.com/hayden0674/ChristmasTree/releases)
- **How to Run**: Unzip the archive and double-click `ParticleChristmasTree.exe`. (If Windows SmartScreen appears, click **More info** -> **Run anyway**.)

#### 🍎 macOS Download
- **Direct Download**: [Download ChristmasTree-macOS.zip](https://github.com/hayden0674/ChristmasTree/releases/latest/download/ChristmasTree-macOS.zip)
- **Release Page**: [GitHub Releases](https://github.com/hayden0674/ChristmasTree/releases)
- **How to Run**: Unzip and open `ParticleChristmasTree.app`, then allow camera access. (If macOS Gatekeeper blocks it on first launch, **Right-click / Control-click the app -> Open**.)

### 2. How to Add Your Photos (1–100 Photos)
- **Method 1 (Shortcut)**: Press **`P`** while the app is running to select multiple images from your computer.
- **Method 2 (Live Folder)**: Drag and drop `.jpg`, `.png`, `.webp`, or `.heic` photos into the **`圣诞树照片库`** folder automatically created on your Desktop. Photos appear on the tree within 1 second with a firework celebration.

### 3. Gesture & Keyboard Controls
- **Open Palm**: Scatter the tree into a 3D starfield (move hand closer/farther to adjust density).
- **Open-Palm Pinch**: Pinch thumb + index while keeping the other 3 fingers extended to zoom in on a photo **while keeping the starfield scattered**.
- **Fist Pinch**: Pinch thumb + index while keeping the other 3 fingers curled to zoom in on a photo **while keeping the Christmas tree assembled**.
- **Fist**: Reassemble particles back into the Christmas tree.
- **Shortcuts**: `P` (add photos) | `Space` (switch themes) | `F` (fireworks) | `R` (replay intro) | `Tab` (fullscreen) | `V` (camera preview) | `ESC` (quit).
