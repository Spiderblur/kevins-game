# Kevin's Game – How to Play

Simple steps for running the game on your computer.

## What you need
- Python 3.13 (download from https://www.python.org if you do not have it)
- `uv` (a tool that installs and runs the game for you)
- Internet for a minute the first time

## Install uv (one time)
In PowerShell:
- `pip install uv`

## Set up and run with uv (Windows PowerShell)
1. Open PowerShell in this folder (`C:\Users\Kevin\Developer\kevins-game`).
2. Let uv install what the game needs and start it:
   - `uv run main.py`
3. A window opens. If you want to stop, press `Esc` or close the window.

## Controls (keep it simple)
- Move: `W`, `A`, `S`, `D`
- Swing sword: left mouse button
- Block with shield: hold right mouse button (uses shield blocks)
- Drink heal potion: `Q` (takes one second to drink)
- Open/close inventory: `T`
- Use a speed potion: left click the potion in your inventory slots
- Buy leather armor (room 3): press `E` when you are near the table and have enough coins
- If you die: press `Space`, `Enter`, or `C` to try again; `Esc` to quit

## Need help?
If something looks confusing, ask for one step at a time. Running `pip install pygame ursina` again is safe if an install fails.***
