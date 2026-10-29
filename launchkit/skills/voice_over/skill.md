# voice_over

Pick me when: the marketer wants sound, e.g. a short voice-over for an ad.
Uses: text_to_speech, check_copy
Hides: text_to_speech (prefer_over)

## Steps

1. Write a script in the brand's voice: at most 25 words for 10 seconds.
2. Call check_copy with the script as the body. Fix any problem it lists.
3. Call text_to_speech with the script.
4. Reply with the script and the file.
