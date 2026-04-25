# TEN VAD integration

Glance uses TEN VAD as the local speech detector for Live turn capture. The
integration keeps Live's existing WAV handoff. Speech detection is required:
if TEN VAD cannot be imported or initialized, Live asks the user to run
`python -m pip install -r requirements.txt` and restart Glance.

Packaged Glance builds should bundle TEN VAD and its native library so users do
not have to install Python dependencies by hand.

Sources:

- TEN VAD repository: https://github.com/TEN-framework/ten-vad
- License: https://raw.githubusercontent.com/TEN-framework/ten-vad/main/LICENSE
- Python example: https://github.com/TEN-framework/ten-vad/blob/main/examples/test.py

TEN VAD is licensed under Apache License 2.0 with additional conditions from
Agora. Review those conditions before distributing a Glance build that bundles
TEN VAD.
