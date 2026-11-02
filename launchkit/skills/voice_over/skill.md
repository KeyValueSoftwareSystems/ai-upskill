# voice_over

Pick me when: the marketer wants sound, e.g. a short voice-over for an ad.
Uses: text_to_speech, check_copy
Hides: text_to_speech (prefer_over)

## Steps

1. Write a script in the brand's voice that fills the time asked: about 2.5 words a second, so about 25 words for 10 seconds.
2. Call check_copy with the script as the body. Fix any problem it lists.
3. Only when check_copy says ok, call text_to_speech with the script.
4. Reply with the script. The chat page plays the file under your reply: do not offer to send it.
