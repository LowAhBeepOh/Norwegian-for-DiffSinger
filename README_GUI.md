# Norwegian for DiffSinger: GUI

A small desktop app that helps you prep Norwegian voicebank data: transcribe audio, auto-label it with Montreal Forced Aligner (MFA), convert the labels to HTK, fix phone names and check labels for errors. The **Pipeline** tab runs all of those in one go.

It's separate from the OpenUtau plugin, so you don't need the GUI to use the plugin.

## Requirements

- **Python 3.10 or newer**, on your PATH.
- **Conda** (Miniforge or Miniconda). Only needed for Auto Label. MFA lives in its own conda env because it depends on Kaldi, which pip can't install.
- Around 5 GB free if you install everything (MFA, the NoFA model and NB-Whisper Small). NB-Whisper Small alone is about 1 GB.

## Install and run

1. Open a terminal in the project folder and install the Python packages:

   ```
   python -m pip install -r gui/requirements.txt
   ```

2. Start the app. On Windows you can just double-click `gui/run_gui.bat`. Otherwise:

   ```
   python -m gui
   ```

3. Go to the **About** tab and press **Install everything for me**. It installs the Python packages and Norwegian MFA with its dictionary, and skips anything that's already installed. NB-Whisper isn't included because it's about 1 GB, so grab it separately with **Install model** on the **Transcribe** tab.

Every control has a hover tip, so rest your pointer on a button for a second to see what it does and which folder to pick.

Long jobs show a progress bar and a **Cancel** button at the bottom of the window. Buttons that start a job are disabled while it runs, so only one job runs at a time.

## Tabs

### About

Shows the GUI and phonemizer versions, the sources, and the **Install everything for me** button.

### Pipeline

Runs the whole prep on one dataset folder, in this order:

1. Transcribe the `.wav` files into `transcriptions/`.
2. Auto-label with MFA. The TextGrids go into `textgrids/`.
3. Convert the TextGrids to `.lab` files in `labs/`, then delete the TextGrids.
4. Fix phonemes: simplify the phone set, then turn pauses with a breath into `AP`. Tick **Skip breathing detection** if you don't want the breath part.
5. Check the labels for errors.

Pick the folder that contains (or will contain) `wavs/`. Missing folders get created for you. The layout is the same as on the Auto Label tab.

### Transcribe

Turns the `.wav` files in a folder into text.

1. Pick a model family (NB-Whisper or Whisper) and a size.
2. If the status says "Not installed", press **Install model**. It downloads once.
3. Pick a folder with `.wav` files and press **Transcribe audio**.

The transcriptions go into a `transcriptions/` folder that sits next to your `wavs/` folder, with one `name.txt` per `name.wav`.

### Auto Label

Aligns audio with its text using Norwegian MFA.

Your folder needs two subfolders:

```
your_folder/
├── wavs/              # .wav files
└── transcriptions/    # .txt files, same names as the .wav files
```

Pick the parent folder (`your_folder`) and press **Start auto-labelling**. The TextGrids go into a new `textgrids/` folder inside it. Files without a matching pair are skipped and listed in the log.

MFA's own output shows up in the terminal the app was started from (the one `run_gui.bat` opens), so keep that window visible while it runs. The log in the GUI only shows the command that ran.

### Convert Format

Turns TextGrid files into HTK `.lab` files, which is what DiffSinger uses.

Pick the folder with your `.TextGrid` files. The `phones` tier of each one becomes a `.lab` file with the same name, written into a new `labs/` folder inside the chosen folder. The TextGrids get deleted afterwards.

### Fix Phonemes

Does two things to the `.lab` files, in this order:

1. Rewrites standard NoFAbet labels (like `AH2`) to the simplified phone set used here (like `ah`), stripping the stress digits. Phones it can't map are listed in the log and left alone.
2. Turns `SP` (silence) into `AP` where the matching `.wav` has an audible breath. The audio is looked up next to the labels first, then in a `wavs` folder, so keep `wavs/` next to `labs/`. Files without matching audio are left alone and reported.

Tick **Skip breathing detection** to keep every pause as `SP` and only run the phone simplification.

This overwrites the `.lab` files in place, so the old versions are gone. Keep a backup if you're unsure.

### Check Auto-Label Errors

Scans `.lab` files for likely alignment problems:

- labels shorter than 22 ms (minor) or 10 ms (major)
- overlapping labels
- zero-length labels

These are only hints, so check the flagged spots by ear before fixing anything.

## Where stuff goes

- Downloaded models, the NoFA files and temporary MFA files go into `.nofa_tools/` in the project folder. It's git-ignored and safe to delete. You'll just have to download things again.
- The MFA conda env is called `nofa-mfa`.

## Limits

- Transcription runs on the CPU, so the big Whisper models are slow on long files.
- Auto-label quality depends on the audio and on how closely the transcription matches what's sung or said.
- Check the labels before training. The check tab catches some errors, but not all of them.
