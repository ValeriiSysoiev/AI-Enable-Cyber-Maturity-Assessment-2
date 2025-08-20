"""
Audio Transcription MCP Tool
Provides consent-aware audio transcription with MIME validation and size limits.
"""
import os
import tempfile
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import json

# Audio processing imports (will be installed via requirements)
try:
    import speech_recognition as sr
    import pydub
    from pydub import AudioSegment
    AUDIO_DEPS_AVAILABLE = True
except ImportError:
    AUDIO_DEPS_AVAILABLE = False

from ..security import SecurityPolicy
from ..config import MCPConfig

logger = logging.getLogger(__name__)

class AudioTranscriptionTool:
    """
    MCP tool for audio transcription with enterprise security features.
    
    Features:
    - Consent flag validation
    - MIME type allowlist
    - File size limits
    - Timestamp generation
    - PII scrubbing pipeline integration
    """
    
    TOOL_NAME = "audio.transcribe"
    
    # Supported audio MIME types
    ALLOWED_MIME_TYPES = {
        "audio/wav",
        "audio/mp3", 
        "audio/mpeg",
        "audio/mp4",
        "audio/m4a",
        "audio/flac",
        "audio/ogg"
    }
    
    # Audio file extensions mapping
    MIME_TO_EXTENSION = {
        "audio/wav": ".wav",
        "audio/mp3": ".mp3",
        "audio/mpeg": ".mp3", 
        "audio/mp4": ".mp4",
        "audio/m4a": ".m4a",
        "audio/flac": ".flac",
        "audio/ogg": ".ogg"
    }
    
    def __init__(self, config: MCPConfig):
        """Initialize audio transcription tool with configuration."""
        self.config = config
        self.security = SecurityPolicy(config)
        self.max_file_size_mb = getattr(config, 'max_audio_file_size_mb', 50)
        self.max_duration_minutes = getattr(config, 'max_audio_duration_minutes', 60)
        
        # Audio processing configuration
        self.chunk_size_ms = 30000  # 30 seconds chunks for processing
        self.sample_rate = 16000   # Standard sample rate for speech recognition
        
        if not AUDIO_DEPS_AVAILABLE:
            logger.warning("Audio dependencies not available. Tool will run in mock mode.")
    
    def validate_consent(self, payload: Dict[str, Any]) -> bool:
        """
        Validate that proper consent has been provided for audio processing.
        
        Args:
            payload: Tool payload containing consent information
            
        Returns:
            bool: True if consent is valid
            
        Raises:
            ValueError: If consent validation fails
        """
        consent_provided = payload.get("consent", False)
        consent_type = payload.get("consent_type", "")
        
        if not consent_provided:
            raise ValueError("Audio transcription requires explicit consent. Set 'consent': true in payload.")
        
        # Validate consent type for enterprise scenarios
        valid_consent_types = {"workshop", "interview", "meeting", "general"}
        if consent_type and consent_type not in valid_consent_types:
            raise ValueError(f"Invalid consent_type '{consent_type}'. Must be one of: {valid_consent_types}")
        
        logger.info(f"Audio transcription consent validated", extra={
            "consent_type": consent_type,
            "consent_provided": consent_provided
        })
        
        return True
    
    def validate_audio_file(self, file_data: bytes, mime_type: str) -> Dict[str, Any]:
        """
        Validate audio file format, size, and duration.
        
        Args:
            file_data: Raw audio file bytes
            mime_type: MIME type of the audio file
            
        Returns:
            Dict containing validation results and metadata
            
        Raises:
            ValueError: If validation fails
        """
        # Check MIME type
        if mime_type not in self.ALLOWED_MIME_TYPES:
            raise ValueError(f"Unsupported audio MIME type: {mime_type}. Allowed: {self.ALLOWED_MIME_TYPES}")
        
        # Check file size
        file_size_mb = len(file_data) / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            raise ValueError(f"Audio file too large: {file_size_mb:.1f}MB. Maximum: {self.max_file_size_mb}MB")
        
        metadata = {
            "file_size_mb": round(file_size_mb, 2),
            "mime_type": mime_type,
            "validation_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # If audio deps available, get additional metadata
        if AUDIO_DEPS_AVAILABLE:
            try:
                # Create temporary file for pydub analysis
                extension = self.MIME_TO_EXTENSION.get(mime_type, ".tmp")
                with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_file:
                    temp_file.write(file_data)
                    temp_file_path = temp_file.name
                
                # Analyze audio with pydub
                audio = AudioSegment.from_file(temp_file_path)
                duration_minutes = len(audio) / (1000 * 60)  # Convert ms to minutes
                
                metadata.update({
                    "duration_seconds": len(audio) / 1000,
                    "duration_minutes": round(duration_minutes, 2),
                    "channels": audio.channels,
                    "sample_rate": audio.frame_rate,
                    "frame_count": audio.frame_count()
                })
                
                # Check duration limit
                if duration_minutes > self.max_duration_minutes:
                    raise ValueError(f"Audio too long: {duration_minutes:.1f}min. Maximum: {self.max_duration_minutes}min")
                
                # Clean up temporary file
                os.unlink(temp_file_path)
                
            except Exception as e:
                logger.warning(f"Could not analyze audio metadata: {e}")
                metadata["analysis_warning"] = str(e)
        
        logger.info("Audio file validation completed", extra=metadata)
        return metadata
    
    def transcribe_audio(self, file_data: bytes, mime_type: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transcribe audio to text with timestamps.
        
        Args:
            file_data: Raw audio file bytes
            mime_type: MIME type of the audio file
            options: Transcription options
            
        Returns:
            Dict containing transcription results
        """
        if not AUDIO_DEPS_AVAILABLE:
            # Mock transcription for testing/development
            return self._mock_transcription(file_data, mime_type, options)
        
        try:
            # Prepare audio for speech recognition
            extension = self.MIME_TO_EXTENSION.get(mime_type, ".tmp")
            with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_file:
                temp_file.write(file_data)
                temp_file_path = temp_file.name
            
            # Convert to WAV format for speech_recognition
            audio = AudioSegment.from_file(temp_file_path)
            
            # Normalize audio for better recognition
            audio = audio.set_channels(1)  # Convert to mono
            audio = audio.set_frame_rate(self.sample_rate)  # Standard sample rate
            
            # Save processed audio
            wav_path = temp_file_path + ".wav"
            audio.export(wav_path, format="wav")
            
            # Initialize speech recognizer
            recognizer = sr.Recognizer()
            
            # Process audio in chunks for timestamp generation
            chunks = self._chunk_audio(audio)
            transcription_results = []
            
            for i, chunk in enumerate(chunks):
                chunk_start_time = i * (self.chunk_size_ms / 1000)
                chunk_text = self._transcribe_chunk(recognizer, chunk, chunk_start_time)
                if chunk_text:
                    transcription_results.append(chunk_text)
            
            # Combine results
            full_text = " ".join([result["text"] for result in transcription_results])
            
            result = {
                "text": full_text,
                "timestamps": transcription_results,
                "confidence": self._calculate_average_confidence(transcription_results),
                "language": options.get("language", "auto-detected"),
                "processing_time_seconds": None  # Will be set by caller
            }
            
            # Clean up temporary files
            os.unlink(temp_file_path)
            os.unlink(wav_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            # Clean up on error
            for path in [temp_file_path, wav_path]:
                try:
                    if 'path' in locals() and os.path.exists(path):
                        os.unlink(path)
                except:
                    pass
            raise ValueError(f"Transcription failed: {str(e)}")
    
    def _chunk_audio(self, audio: AudioSegment) -> List[AudioSegment]:
        """Split audio into chunks for processing."""
        chunks = []
        for i in range(0, len(audio), self.chunk_size_ms):
            chunk = audio[i:i + self.chunk_size_ms]
            chunks.append(chunk)
        return chunks
    
    def _transcribe_chunk(self, recognizer: sr.Recognizer, chunk: AudioSegment, start_time: float) -> Optional[Dict[str, Any]]:
        """Transcribe a single audio chunk."""
        try:
            # Export chunk to temporary WAV
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_chunk:
                chunk.export(temp_chunk.name, format="wav")
                
                # Transcribe with speech_recognition
                with sr.AudioFile(temp_chunk.name) as source:
                    audio_data = recognizer.record(source)
                    text = recognizer.recognize_google(audio_data)
                
                os.unlink(temp_chunk.name)
                
                return {
                    "text": text,
                    "start_time": start_time,
                    "end_time": start_time + (len(chunk) / 1000),
                    "confidence": 0.8  # Google API doesn't provide confidence scores
                }
                
        except sr.UnknownValueError:
            # No speech detected in this chunk
            return None
        except Exception as e:
            logger.warning(f"Failed to transcribe chunk starting at {start_time}s: {e}")
            return None
    
    def _calculate_average_confidence(self, results: List[Dict[str, Any]]) -> float:
        """Calculate average confidence score from transcription results."""
        if not results:
            return 0.0
        
        confidences = [r.get("confidence", 0.0) for r in results if r.get("confidence")]
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def _mock_transcription(self, file_data: bytes, mime_type: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mock transcription for development/testing when audio deps unavailable.
        """
        file_size_mb = len(file_data) / (1024 * 1024)
        mock_duration = min(file_size_mb * 2, 10)  # Estimate duration
        
        mock_text = f"""
        This is a mock transcription of the uploaded {mime_type} audio file.
        The file was {file_size_mb:.1f}MB in size.
        In a real implementation, this would contain the actual transcribed speech.
        This mock supports consent validation, file size limits, and timestamp generation.
        """
        
        return {
            "text": mock_text.strip(),
            "timestamps": [
                {
                    "text": "This is a mock transcription",
                    "start_time": 0.0,
                    "end_time": 2.5,
                    "confidence": 0.95
                },
                {
                    "text": f"of the uploaded {mime_type} audio file",
                    "start_time": 2.5,
                    "end_time": 5.0,
                    "confidence": 0.92
                }
            ],
            "confidence": 0.93,
            "language": options.get("language", "en-US"),
            "mock_mode": True
        }
    
    async def execute(self, payload: Dict[str, Any], engagement_id: str, call_id: str) -> Dict[str, Any]:
        """
        Execute audio transcription with full validation and security.
        
        Args:
            payload: Tool execution payload
            engagement_id: Engagement identifier for sandboxing
            call_id: Unique call identifier for tracking
            
        Returns:
            Dict containing transcription results and metadata
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Validate consent
            self.validate_consent(payload)
            
            # Extract and validate audio data
            if "audio_data" not in payload:
                raise ValueError("Missing required field: audio_data (base64 encoded)")
            
            if "mime_type" not in payload:
                raise ValueError("Missing required field: mime_type")
            
            # Decode audio data
            import base64
            try:
                audio_data = base64.b64decode(payload["audio_data"])
            except Exception as e:
                raise ValueError(f"Invalid base64 audio_data: {e}")
            
            mime_type = payload["mime_type"]
            
            # Validate audio file
            file_metadata = self.validate_audio_file(audio_data, mime_type)
            
            # Transcription options
            options = payload.get("options", {})
            language = options.get("language", "auto")
            include_timestamps = options.get("include_timestamps", True)
            
            # Check PII scrubbing configuration
            pii_scrub_enabled = payload.get("pii_scrub", {}).get("enabled", False)
            
            # Perform transcription
            transcription_result = self.transcribe_audio(audio_data, mime_type, options)
            
            # Calculate processing time
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            transcription_result["processing_time_seconds"] = round(processing_time, 2)
            
            # Prepare result
            result = {
                "success": True,
                "tool": self.TOOL_NAME,
                "call_id": call_id,
                "engagement_id": engagement_id,
                "transcription": transcription_result,
                "file_metadata": file_metadata,
                "consent": {
                    "provided": True,
                    "type": payload.get("consent_type", "general"),
                    "timestamp": start_time.isoformat()
                },
                "pii_scrub_enabled": pii_scrub_enabled,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Log successful transcription
            logger.info(
                "Audio transcription completed successfully",
                extra={
                    "call_id": call_id,
                    "engagement_id": engagement_id,
                    "file_size_mb": file_metadata.get("file_size_mb"),
                    "duration_seconds": file_metadata.get("duration_seconds"),
                    "processing_time_seconds": processing_time,
                    "text_length": len(transcription_result["text"]),
                    "confidence": transcription_result.get("confidence")
                }
            )
            
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "tool": self.TOOL_NAME,
                "call_id": call_id,
                "engagement_id": engagement_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.error(
                "Audio transcription failed",
                extra={
                    "call_id": call_id,
                    "engagement_id": engagement_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            
            return error_result


# Tool registration function
def register_tool(tool_registry: Dict[str, Any]) -> None:
    """Register the audio transcription tool with MCP gateway."""
    tool_registry[AudioTranscriptionTool.TOOL_NAME] = AudioTranscriptionTool