"""Gesture control: validates recognised gestures and turns them into device commands.

Recognition itself (camera + MediaPipe) runs in the browser; this package only
receives the result (gesture, intent, confidence) and never sees video frames.
"""
