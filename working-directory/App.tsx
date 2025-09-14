import React, { useState, useEffect, useRef } from 'react';
import './App.css';

interface RecordingState {
  isRecording: boolean;
  isProcessing: boolean;
  audioBlob: Blob | null;
  transcribedText: string;
  signVideoUrl: string | null;
}

export default function App() {
  const [recordingState, setRecordingState] = useState<RecordingState>({
    isRecording: false,
    isProcessing: false,
    audioBlob: null,
    transcribedText: '',
    signVideoUrl: null,
  });

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  // Initialize microphone access
  useEffect(() => {
    const initializeMicrophone = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });
        streamRef.current = stream;
      } catch (error) {
        console.error('Error accessing microphone:', error);
      }
    };

    initializeMicrophone();

    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  // Handle spacebar key events
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (
        event.code === 'Space' &&
        !recordingState.isRecording &&
        !recordingState.isProcessing
      ) {
        event.preventDefault();
        startRecording();
      }
    };

    const handleKeyUp = (event: KeyboardEvent) => {
      if (event.code === 'Space' && recordingState.isRecording) {
        event.preventDefault();
        stopRecording();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [recordingState.isRecording, recordingState.isProcessing]);

  const startRecording = async () => {
    if (!streamRef.current) return;

    try {
      const mediaRecorder = new MediaRecorder(streamRef.current);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: 'audio/wav',
        });
        setRecordingState((prev) => ({
          ...prev,
          audioBlob,
          isProcessing: true,
        }));
        processAudio(audioBlob);
      };

      mediaRecorder.start();
      setRecordingState((prev) => ({ ...prev, isRecording: true }));
    } catch (error) {
      console.error('Error starting recording:', error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && recordingState.isRecording) {
      mediaRecorderRef.current.stop();
      setRecordingState((prev) => ({ ...prev, isRecording: false }));
    }
  };

  // const processAudio = async (audioBlob: Blob) => {
  //   // Send .wav file to server
  //   try {
  //     const formData = new FormData();
  //     formData.append('file', audioBlob, 'audio.wav');
  //     const response = await fetch('http://127.0.0.1:7777/transcribe', {
  //       method: 'POST',
  //       body: formData,
  //     });
  //     if (!response.ok) {
  //       throw new Error('Failed to upload audio');
  //     }
  //     const data = await response.json();
  //     // Expecting { transcribedText: string, videoUrl: string }
  //     setRecordingState((prev) => ({
  //       ...prev,
  //       transcribedText: data.transcribedText || '',
  //       signVideoUrl: "https://www.w3schools.com/html/mov_bbb.mp4", // data.videoUrl || null,
  //       isProcessing: false,
  //     }));
  //   } catch (error) {
  //     console.error('Error processing audio:', error);
  //     setRecordingState((prev) => ({
  //       ...prev,
  //       isProcessing: false,
  //     }));
  //   }
  // };

  const processAudio = async (audioBlob: Blob) => {
    try {
      // Step 1: Send to /transcribe
      const formData = new FormData();
      formData.append("file", audioBlob, "audio.wav");
      const resp = await fetch("http://127.0.0.1:7777/transcribe", {
        method: "POST",
        body: formData,
      });
      if (!resp.ok) throw new Error("Transcribe failed");
      const data = await resp.json();

      // Step 2: Call inference with text
      const infResp = await fetch("http://127.0.0.1:8000/inference", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: data.transcribedText }),
      });
      if (!infResp.ok) throw new Error("Inference failed");
      const infData = await infResp.json();

      console.log("inference data:", infData);
      // Step 3: Update state with stitched video path
      setRecordingState((prev) => ({
        ...prev,
        transcribedText: infData.input,
        signVideoUrl: "http://127.0.0.1:8000/" + infData.stitched_video, // serve file via static
        isProcessing: false,
      }));
    } catch (err) {
      console.error("Error processing:", err);
      setRecordingState((prev) => ({ ...prev, isProcessing: false }));
    }
  };

  //   const processAudio = async (audioBlob: Blob) => {
  //   try {
  //     const formData = new FormData();
  //     formData.append('file', audioBlob, 'audio.wav');
  //     const response = await fetch('http://127.0.0.1:7777/transcribe', {
  //       method: 'POST',
  //       body: formData,
  //     });
  //     const data = await response.json();

  //     // Simulate server processing delay
  //     await new Promise((resolve) => setTimeout(resolve, 2000));

  //     // Dummy data
  //     const dummyText = "Hello, this is a test transcription.";
  //     const dummyVideoUrl =
  //       "https://www.w3schools.com/html/mov_bbb.mp4"; // public sample video

  //     setRecordingState((prev) => ({
  //       ...prev,
  //       transcribedText: dummyText,
  //       signVideoUrl: dummyVideoUrl,
  //       isProcessing: false,
  //     }));
  //   } catch (error) {
  //     console.error("Error in dummy processAudio:", error);
  //     setRecordingState((prev) => ({
  //       ...prev,
  //       isProcessing: false,
  //     }));
  //   }
  // };

  const resetApp = () => {
    setRecordingState({
      isRecording: false,
      isProcessing: false,
      audioBlob: null,
      transcribedText: '',
      signVideoUrl: null,
    });
  };

  return (
    <div className="app">
      <div className="container">
        <header className="header">
          <h1>Speech to Sign Language</h1>
          <p>Hold the spacebar to record your speech</p>
        </header>

        <div className="main-content">
          {/* Recording Area */}
          <div className="recording-area">
            <div
              className={`microphone-container ${recordingState.isRecording ? 'recording' : ''}`}
            >
              <div className="microphone">
                <svg
                  width="80"
                  height="80"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                  <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
                </svg>
              </div>
              <div className="pulse-ring"></div>
              <div className="pulse-ring-2"></div>
            </div>

            <div className="status-text">
              {recordingState.isProcessing && (
                <div className="processing">
                  <div className="spinner"></div>
                  <span>Processing audio...</span>
                </div>
              )}
              {recordingState.isRecording && (
                <span className="recording-text">
                  Recording... Release spacebar to stop
                </span>
              )}
              {!recordingState.isRecording &&
                !recordingState.isProcessing &&
                !recordingState.transcribedText && (
                  <span className="instruction-text">
                    Hold spacebar to start recording
                  </span>
                )}
            </div>
          </div>

          {/* Results Area */}
          {(recordingState.transcribedText || recordingState.signVideoUrl) && (
            <div className="results-area">
              <div className="transcription">
                <h3>Transcribed Text:</h3>
                <p>{recordingState.transcribedText}</p>
              </div>

              {recordingState.signVideoUrl && (
                <div className="sign-video">
                  <h3>Sign Language Video:</h3>
                  <video
                    controls
                    autoPlay
                    loop
                    src={recordingState.signVideoUrl}
                    className="video-player"
                  >
                    Your browser does not support the video tag.
                  </video>
                </div>
              )}

              <button onClick={resetApp} className="reset-button">
                Record Again
              </button>
            </div>
          )}
        </div>

        <footer className="footer">
          <p>Press and hold the spacebar to record your speech</p>
        </footer>
      </div>
    </div>
  );
}
