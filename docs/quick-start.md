# Quick start

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) once, then
open Bash (Git Bash on Windows) in this repository. `uv run` manages the project
environment and USB dependency for you.

1. Connect the HDC3020EVM by USB and close TI's EVM GUI. If several USB2ANY
   bridges are connected, enter the target board's USB serial in the dashboard.
2. Start the dashboard:

   ```bash
   uv run --extra usb python app.py
   ```

3. Open [http://127.0.0.1:8050/](http://127.0.0.1:8050/). Select **USB /
   USB2ANY HID**, address **0x44**, interval **1 s**, then click **Start
   monitoring**. The temperature and humidity readings should update together;
   **Failed reads** should stay at zero. The checked **Save CSV automatically**
   option starts logging after connection succeeds.
4. Watch **CSV recording** for the filename, row count and dropped-row count.
   The app starts a new file on the first sample of each UTC day. To download
   the current file while still connected, click **Stop recording** →
   **Download last CSV**. Earlier daily files remain in `recordings/`.
   Uncheck auto-save before starting for a view without a file; **Record**
   is available for manual capture.
5. Click **Disconnect** to drain an active recording and release the board,
   then press **Ctrl+C** in Bash. Closing the browser tab alone does not
   release the board.

To try the interface without a board, run `uv run python app.py --simulate` and
select **Simulation · no hardware**. For plots, settings and troubleshooting,
see the [usage guide](usage-guide.md). Leave the sensor's optional
integrated heater off during normal monitoring ([current status](../STATE.md)).
