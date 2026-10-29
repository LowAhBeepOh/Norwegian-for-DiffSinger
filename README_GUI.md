# Norwegian for DiffSinger: GUI

A small desktop app that helps you prepare Norwegian voicebank data: transcribe audio, auto-label it with Montreal Forced Aligner (MFA), convert the labels to HTK, fix phone names, and check labels for errors.

It is separate from the OpenUtau plugin. You don't need the GUI to use the plugin.

## Requirements

- **Python 3.10 or newer**, with Python on your PATH.
- **Conda** (Miniforge or Miniconda). Only needed for Auto Label. MFA is installed in its own conda environment because it depends on Kaldi, which pip can't install.
- Around 5 GB of free disk space if you install everything (MFA, the NoFA model and NB-Whisper Small). NB-Whisper Small alone is about 1 GB.

## Install and run

1. Open a terminal in the project folder and install the Python packages:

   ```
   python -m pip install -r gui/requirements.txt
   ```

2. Start the app. On Windows you can double-click `gui/run_gui.bat`. Otherwise run:

   ```
   python -m gui
   ```

3. Go to the **About** tab and press **Install everything for me**. It installs the Python packages and Norwegian MFA with its dictionary. Steps that are already installed are skipped. NB-Whisper is not included because it's about 1 GB, so install it separately with **Install model** on the **Transcribe** tab.

Every control has a hover tip. Rest the pointer on a button for about a second to see what it does and which folder to choose.

## Tabs

### About

Shows the GUI and phonemizer versions, the sources for the GUI and its tools, and the **Install everything for me** button.

### Transcribe

Turns the `.wav` files in a folder into text.

1. Choose the model family (NB-Whisper or Whisper) and a size.
2. Press **Install model** if the status says "Not installed". This downloads the model once.
3. Choose a folder with `.wav` files and press **Transcribe audio**.

Each `name.wav` gets a `name.txt` next to it, with the transcription.

### Auto Label

Aligns audio with its text using Norwegian MFA.

Your folder must contain two subfolders:

```
your_folder/
├── wavs/              # .wav files
└── transcriptions/    # .txt files, same names as the .wav files
```

Choose the parent folder (`your_folder`) and press **Start auto-labelling**. The TextGrid results go into a new `labels/` folder inside it. Files without a matching pair are skipped and reported in the log.

### Convert Format

Converts TextGrid files to HTK `.lab` files, which is the format DiffSinger uses.

Choose the folder with your `.TextGrid` files and check the tier name (MFA usually uses `phones`). Each TextGrid is converted to a `.lab` file with the same name, in the same folder.

### Fix Phonemes

Rewrites standard NoFAbet labels (for example `AH2`) to the simplified phone set used by this project (for example `ah`). It strips the stress digits. Phones it can't map are listed in the log and left unchanged.

The `.lab` files are rewritten in place. Keep a backup if you're unsure.

### Check Auto-Label Errors

Scans `.lab` files for likely alignment problems:

- labels shorter than 22 ms (minor) or 10 ms (major)
- overlapping labels
- zero-length labels

The results are hints. Check the flagged spots by ear before you fix anything.

## Where things are stored

- Downloaded models, the NoFA files and temporary MFA files go into `.nofa_tools/` in the project folder. This folder is git-ignored and safe to delete. It only costs you a re-download.
- The MFA conda environment is named `nofa-mfa`.

## Limits

- Transcription runs on the CPU, so large Whisper models are slow on long files.
- Auto-labelling quality depends on the audio and on how closely the transcription matches what is sung or said.
- Check the labels before training. The check tab catches some errors, but not all.
