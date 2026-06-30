# MineDesktop

A very simple desktop mate program that displays a Minecraft-themed GIF Image.

![Demo](./imgs/creeper_n.gif)

## Usage

Download the newest release, unzip it, and run `pet.exe`.
 
## Configuration

Themes are configured in `themes.json`:

```python
{
    "themes": [
        {
            "name": "Theme Name",
            "main_gif": "path/to/GIF/image",
            "click_gif": "path/to/animation/image",
            "mode": "wait"
                # wait: After click, a complete cycle of the main GIF will be played before the animation (for better linkage).
                # immediate: The main GIF will be interrupted and the animation will be played immediately after click.
        },
        ...
    ]
}
```

## Build

Clone the repository

```cmd
git clone https://github.com/sclass53/MineDesktop.git .
```

Run
```cmd
pyinstaller --noconsole --onefile pet.py
```
