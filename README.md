# Voice AI

Android + web client for video dubbing.

## Current engine

The backend now connects to the ElevenLabs Dubbing Projects API (dubbing_v2):
- Uploads a source video.
- Queues an automatic Spanish dub.
- Checks the provider's project/language status.
- Downloads the generated lossless audio and muxes it back onto the original video with FFmpeg, keeping the original video stream and resolution.

The provider supports audio/video source files up to 3 GiB. Dubbing is a paid API operation and the provider charges for the first target language when a project is created. Check your ElevenLabs plan and usage before processing long videos.

Current limitations:
- The API key and a deployed backend are required. Never put the API key in the Android app or GitHub.
- The server uses an in-memory job registry; a server restart loses job tracking.
- The automatic dubbing provider preserves/replicates detected speakers; the single-voice selector in the UI is not yet wired to a fixed voice.
- Custom-script dubbing and OCR/replacement of text embedded in the video are not implemented yet.
- The provider returns dubbed audio; FFmpeg muxes it onto the original video. Output keeps the source video resolution; this does not upscale to 4K.

## Deploy backend

1. Create a Render account and connect this GitHub repository.
2. Deploy using the repository's `render.yaml` Blueprint.
3. Set `ELEVENLABS_API_KEY` as a secret environment variable in Render. Do not commit it.
4. Wait for the service health check at `/health`.
5. Set the deployed API base URL in the Android/web client and rebuild the APK.

Required service: FFmpeg is installed in the Docker image. A persistent disk is configured for source/output media. The Render Starter service and persistent disk may incur charges, separate from ElevenLabs usage.

## Android

The GitHub Actions workflow builds a debug APK on each push to `main`.
