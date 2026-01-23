# Vibe Racer

Top-down racing prototype built with Pygame. Includes time trials, ghosts, creator validation runs, and a track editor.

## Run

```bash
uv run -m src.main
```

## How To Play

### Main Menu

- Up/Down=move, Enter=select, Q=quit
- Race: pick a track and drive to finish as fast as possible.
- Color: choose your car color.
- Track editor: create or edit tracks (creator-only; hidden toggle).
- About: credits and car models.

### Racing Controls

- Up/Down/Left/Right: drive and steer
- R: restart
- P: clear best time
- G: toggle player ghost
- C: toggle creator ghost (only after beating creator time)
- B: back to track select
- Q: quit

### Track Editor

- Arrows=move, Space=paint, R=rotate start, S=test+save, B=back
- Tile Type: 0=road, 1=wall, 2=mud, 3=start, 4=finish, 5=checkpoint
- Current Tile shown at top. Cursor draws selected tile.
- S runs a validation drive; finish to save and store creator time.

## Options & Features

- Best times are saved per track.
- Player ghost saves your best run and replays it if compatible.
- Creator ghost saves after validation and can be toggled once beaten.
- Mud slows acceleration, speed, and turning with a short sticky effect.

## Advanced (Cheat Codes)

These only work on the main menu.

- 2+4+7: toggle creator mode (hidden)
    - you can also modify tracks 1-3 in creator mode
- 2+5+0: reset all player best times and ghosts
- 1+3+7: toggle cheater mode (marks creator records as beaten)
