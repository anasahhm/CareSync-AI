/**
 * GestureMed AI — WebRTC Hook
 * Manages peer connection, local/remote streams, and signaling via Socket.IO.
 */
"use client";

import { useEffect, useRef, useState, useCallback } from "react";

const ICE_SERVERS: RTCConfiguration = {
  iceServers: [
    { urls: "stun:stun.l.google.com:19302" },
    { urls: "stun:stun1.l.google.com:19302" },
  ],
};

interface UseWebRTCOptions {
  onOffer: (offer: RTCSessionDescriptionInit) => void;
  onAnswer: (answer: RTCSessionDescriptionInit) => void;
  onICECandidate: (candidate: RTCIceCandidateInit) => void;
  isInitiator: boolean;
}

export function useWebRTC(options: UseWebRTCOptions) {
  const peerRef = useRef<RTCPeerConnection | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [remoteStream, setRemoteStream] = useState<MediaStream | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initLocalStream = useCallback(async (video = true, audio = true) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video, audio });
      localStreamRef.current = stream;
      setLocalStream(stream);
      return stream;
    } catch (err) {
      setError("Camera/microphone access denied");
      throw err;
    }
  }, []);

  const createPeerConnection = useCallback(() => {
    const pc = new RTCPeerConnection(ICE_SERVERS);

    pc.onicecandidate = (event) => {
      if (event.candidate) {
        options.onICECandidate(event.candidate.toJSON());
      }
    };

    pc.ontrack = (event) => {
      const [remote] = event.streams;
      setRemoteStream(remote);
    };

    pc.onconnectionstatechange = () => {
      setIsConnected(pc.connectionState === "connected");
    };

    // Add local tracks
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach((track) => {
        pc.addTrack(track, localStreamRef.current!);
      });
    }

    peerRef.current = pc;
    return pc;
  }, [options]);

  const startCall = useCallback(async () => {
    const pc = createPeerConnection();
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    options.onOffer(offer);
  }, [createPeerConnection, options]);

  const handleOffer = useCallback(async (offer: RTCSessionDescriptionInit) => {
    const pc = createPeerConnection();
    await pc.setRemoteDescription(offer);
    const answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);
    options.onAnswer(answer);
  }, [createPeerConnection, options]);

  const handleAnswer = useCallback(async (answer: RTCSessionDescriptionInit) => {
    if (peerRef.current) {
      await peerRef.current.setRemoteDescription(answer);
    }
  }, []);

  const handleICECandidate = useCallback(async (candidate: RTCIceCandidateInit) => {
    if (peerRef.current) {
      await peerRef.current.addIceCandidate(new RTCIceCandidate(candidate));
    }
  }, []);

  const toggleVideo = useCallback((enabled: boolean) => {
    localStreamRef.current?.getVideoTracks().forEach((t) => (t.enabled = enabled));
  }, []);

  const toggleAudio = useCallback((enabled: boolean) => {
    localStreamRef.current?.getAudioTracks().forEach((t) => (t.enabled = enabled));
  }, []);

  const endCall = useCallback(() => {
    localStreamRef.current?.getTracks().forEach((t) => t.stop());
    peerRef.current?.close();
    setLocalStream(null);
    setRemoteStream(null);
    setIsConnected(false);
  }, []);

  useEffect(() => {
    return () => {
      endCall();
    };
  }, [endCall]);

  return {
    localStream,
    remoteStream,
    isConnected,
    error,
    initLocalStream,
    startCall,
    handleOffer,
    handleAnswer,
    handleICECandidate,
    toggleVideo,
    toggleAudio,
    endCall,
  };
}
