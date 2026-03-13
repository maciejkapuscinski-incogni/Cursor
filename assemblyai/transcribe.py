"""
Transcription script using AssemblyAI API.

This script transcribes audio files using AssemblyAI's transcription service.
Can also batch transcribe videos from Facebook CDN URLs found in RTF files.
"""

import os
import sys
import re
import csv
from urllib.parse import urlparse

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, skip loading .env file
    pass

import assemblyai as aai
from assemblyai import TranscriptionConfig


def transcribe_file(audio_file_path: str, api_key: str = None) -> str:
    """
    Transcribe an audio file using AssemblyAI.
    
    Args:
        audio_file_path: Path to the audio file to transcribe
        api_key: AssemblyAI API key (optional, can be set via ASSEMBLYAI_API_KEY env var)
    
    Returns:
        The transcribed text as a string
    """
    # Get API key from parameter or environment variable
    if api_key is None:
        api_key = os.getenv("ASSEMBLYAI_API_KEY")
        if api_key is None:
            raise ValueError(
                "API key not provided. Set ASSEMBLYAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
    
    # Set API key as environment variable for AssemblyAI SDK
    os.environ["ASSEMBLYAI_API_KEY"] = api_key
    
    # Check if file exists
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
    
    # Initialize transcriber
    transcriber = aai.Transcriber()
    
    # Create config with speech model
    config = aai.TranscriptionConfig(speech_models=["universal-2"])
    
    # Transcribe the file
    print(f"Transcribing {audio_file_path}...")
    transcript = transcriber.transcribe(audio_file_path, config=config)
    
    # Wait for transcription to complete
    transcript.wait_for_completion()
    
    # Check for errors
    if transcript.status == "error":
        error_msg = transcript.error if hasattr(transcript, "error") else "Unknown error"
        raise Exception(f"Transcription failed: {error_msg}")
    
    # Return the transcribed text
    return transcript.text


def transcribe_url(video_url: str, api_key: str = None) -> str:
    """
    Transcribe a video from a URL using AssemblyAI.
    
    Args:
        video_url: URL of the video to transcribe
        api_key: AssemblyAI API key (optional, can be set via ASSEMBLYAI_API_KEY env var)
    
    Returns:
        The transcribed text as a string
    """
    # Get API key from parameter or environment variable
    if api_key is None:
        api_key = os.getenv("ASSEMBLYAI_API_KEY")
        if api_key is None:
            raise ValueError(
                "API key not provided. Set ASSEMBLYAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
    
    # Set API key as environment variable for AssemblyAI SDK
    os.environ["ASSEMBLYAI_API_KEY"] = api_key
    
    # Initialize transcriber
    transcriber = aai.Transcriber()
    
    # Create config with speech model
    config = aai.TranscriptionConfig(speech_models=["universal-2"])
    
    # Transcribe from URL
    print(f"Transcribing video from URL: {video_url[:80]}...")
    transcript = transcriber.transcribe(video_url, config=config)
    
    # Wait for transcription to complete
    transcript.wait_for_completion()
    
    # Check for errors
    if transcript.status == "error":
        error_msg = transcript.error if hasattr(transcript, "error") else "Unknown error"
        raise Exception(f"Transcription failed: {error_msg}")
    
    # Return the transcribed text
    return transcript.text


def transcribe_file_to_file(
    audio_file_path: str, 
    output_file_path: str = None,
    api_key: str = None
) -> str:
    """
    Transcribe an audio file and save the result to a text file.
    
    Args:
        audio_file_path: Path to the audio file to transcribe
        output_file_path: Path to save the transcription (optional)
        api_key: AssemblyAI API key (optional, can be set via ASSEMBLYAI_API_KEY env var)
    
    Returns:
        The transcribed text as a string
    """
    # Transcribe the file
    text = transcribe_file(audio_file_path, api_key)
    
    # Determine output file path
    if output_file_path is None:
        base_name = os.path.splitext(audio_file_path)[0]
        output_file_path = f"{base_name}_transcript.txt"
    
    # Save to file
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(text)
    
    print(f"Transcription saved to: {output_file_path}")
    return text


def extract_urls_from_rtf(rtf_file_path: str) -> list:
    """
    Extract all URLs from an RTF file.
    
    Args:
        rtf_file_path: Path to the RTF file containing URLs
    
    Returns:
        List of extracted URLs
    """
    if not os.path.exists(rtf_file_path):
        raise FileNotFoundError(f"RTF file not found: {rtf_file_path}")
    
    print(f"Reading RTF file: {rtf_file_path}")
    with open(rtf_file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    # Extract URLs using regex (matches http/https URLs)
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, content)
    
    # Remove trailing backslashes and RTF formatting characters
    cleaned_urls = []
    for url in urls:
        # Clean up URL (remove RTF escape sequences and trailing characters)
        url = url.rstrip('\\').rstrip('}').rstrip('{').rstrip(' ')
        # Remove RTF cell markers if present
        url = url.replace('\\cell', '').replace('\\row', '')
        if url.startswith('http'):
            cleaned_urls.append(url)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_urls = []
    for url in cleaned_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    
    print(f"Found {len(unique_urls)} unique URLs")
    return unique_urls


def transcribe_all_from_rtf(
    rtf_file_path: str,
    output_csv: str = None,
    api_key: str = None
) -> dict:
    """
    Transcribe all videos from URLs found in an RTF file and save to CSV.
    
    Args:
        rtf_file_path: Path to the RTF file containing video URLs
        output_csv: Path to output CSV file (default: "transcriptions.csv")
        api_key: AssemblyAI API key (optional, can be set via ASSEMBLYAI_API_KEY env var)
    
    Returns:
        Dictionary mapping URLs to their transcription results
    """
    # Extract URLs from RTF file
    urls = extract_urls_from_rtf(rtf_file_path)
    
    if not urls:
        print("No URLs found in RTF file.")
        return {}
    
    # Determine output CSV file path
    if output_csv is None:
        base_name = os.path.splitext(rtf_file_path)[0]
        output_csv = f"{base_name}_transcriptions.csv"
    
    # Get API key
    if api_key is None:
        api_key = os.getenv("ASSEMBLYAI_API_KEY")
        if api_key is None:
            raise ValueError(
                "API key not provided. Set ASSEMBLYAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
    
    # Set API key as environment variable for AssemblyAI SDK (set once for all transcriptions)
    os.environ["ASSEMBLYAI_API_KEY"] = api_key
    
    results = {}
    successful = 0
    failed = 0
    
    print(f"\nStarting transcription of {len(urls)} videos...\n")
    
    # Prepare CSV data
    csv_data = []
    
    for i, url in enumerate(urls, 1):
        try:
            print(f"[{i}/{len(urls)}] Processing video {i}...")
            
            # Transcribe the video
            text = transcribe_url(url, api_key)
            
            # Store result
            results[url] = {
                "status": "success",
                "text": text
            }
            csv_data.append([url, text])
            successful += 1
            print(f"✓ Successfully transcribed video {i}\n")
            
        except Exception as e:
            error_msg = str(e)
            results[url] = {
                "status": "error",
                "error": error_msg
            }
            # Store error in transcription column
            csv_data.append([url, f"ERROR: {error_msg}"])
            failed += 1
            print(f"✗ Failed to transcribe video {i}: {error_msg}\n")
    
    # Write to CSV file
    print(f"\nWriting results to CSV file: {output_csv}")
    with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow(["Video Link", "Transcription"])
        # Write all rows
        writer.writerows(csv_data)
    
    print(f"\n{'='*50}")
    print(f"Transcription complete!")
    print(f"Total: {len(urls)} | Successful: {successful} | Failed: {failed}")
    print(f"Results saved to: {output_csv}")
    print(f"{'='*50}")
    
    return results


def main():
    """Main function for command-line usage."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python transcribe.py <audio_file> [output_file]")
        print("  python transcribe.py --batch <rtf_file> [output_csv]")
        print("\nExamples:")
        print("  python transcribe.py audio.mp3")
        print("  python transcribe.py audio.mp3 transcript.txt")
        print("  python transcribe.py --batch vids_guard.rtf")
        print("  python transcribe.py --batch vids_guard.rtf transcriptions.csv")
        sys.exit(1)
    
    # Check if batch mode
    if sys.argv[1] == "--batch":
        if len(sys.argv) < 3:
            print("Error: RTF file path required for batch mode")
            print("Usage: python transcribe.py --batch <rtf_file> [output_csv]")
            sys.exit(1)
        
        rtf_file = sys.argv[2]
        output_csv = sys.argv[3] if len(sys.argv) > 3 else None
        
        try:
            transcribe_all_from_rtf(rtf_file, output_csv)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Single file mode
        audio_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        
        try:
            text = transcribe_file_to_file(audio_file, output_file)
            print("\nTranscription completed successfully!")
            print(f"\nTranscribed text:\n{text}")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

