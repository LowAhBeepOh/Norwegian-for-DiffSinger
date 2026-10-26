# Credits

- **NST Pronunciation Lexicon for Norwegian Bokmål**, originally produced by Nordisk språkteknologi (NST) and distributed by the National Library of Norway (Språkbanken, resource `oai-nb-no-sbr-23`). The G2P model is trained on this lexicon, which is released under CC0 1.0: https://creativecommons.org/publicdomain/zero/1.0/
- **NoFAbet**, the phone notation this project uses, developed by Nate Young for the National Library of Norway. This project uses a simplified subset without stress or tone markings.
- **OpenUtau** and its DiffSinger phonemizers, the host this plugin runs in. The plugin is built against `OpenUtau.Core`.
- **DiffSinger** (OpenVPI), the acoustic model family the voicebanks use.
- **openutau/g2p** and StAkira's G2P work, the RNN-T training pipeline this model is based on.
- **Phonetisaurus** (BSD 3-Clause), a related G2P project. Not used in this repo, but its lexicon and evaluation notes were a useful reference.
- **Microsoft ONNX Runtime**, used for inference.
