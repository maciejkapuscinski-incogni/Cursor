# AssemblyAI Transcription Script

A Python script to transcribe audio/video files and batch transcribe videos from Facebook CDN URLs.

## Setup

1. **Install dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

2. **Set up your API key:**
   
   Create a `.env` file in this directory:
   ```bash
   echo 'ASSEMBLYAI_API_KEY=your-api-key-here' > .env
   ```
   
   Or manually create `.env` and add:
   ```
   ASSEMBLYAI_API_KEY=your-api-key-here
   ```
   
   Replace `your-api-key-here` with your actual AssemblyAI API key.

## Usage

### Single file transcription:
```bash
python3 transcribe.py audio.mp3
python3 transcribe.py audio.mp3 output.txt
```

### Batch transcription from RTF file:
```bash
python3 transcribe.py --batch vids_guard.rtf
python3 transcribe.py --batch vids_guard.rtf transcriptions.csv
```

The batch mode will:
- Extract all video URLs from the RTF file
- Transcribe each video using AssemblyAI
- Save results to a CSV file with two columns: Video Link and Transcription

## Output

Batch transcription creates a CSV file with:
- **Column 1**: Video Link (Facebook CDN URL)
- **Column 2**: Full Transcription (or error message if transcription failed)

## Notes

- The `.env` file is gitignored and will not be committed to version control
- Make sure your AssemblyAI API key has sufficient credits for the number of videos you want to transcribe

