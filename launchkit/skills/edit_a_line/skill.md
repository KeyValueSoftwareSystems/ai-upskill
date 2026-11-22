# edit_a_line

Pick me when: the marketer asks to change, fix, replace or take out one line or phrase of text already written in a brief or draft, and may not say where it is.
Uses: search_files, read_file, edit_file
Needs: search_files, read_file, edit_file

## Steps

1. If the marketer named the file, go to step 3. Otherwise call search_files with one distinctive word from the line they described, such as a rare word or a hyphenated one, not the whole phrase: the search matches exact text only. If nothing matches, retry with a different single word before you say you cannot find it.
2. If more than one file or line matches, list each as its path and snippet, ask which one they mean, and stop: do not edit anything until they answer. Never choose one yourself, and never edit more than one.
3. Read the lines around the match with read_file, using first_line and last_line.
4. Call edit_file with the old text copied exactly from the file and the new text. If it says Not found or Ambiguous, read the lines again and retry once with more of the surrounding text.
5. Check the result says Edited. Only then tell the marketer which file and line you changed, in one sentence. If it did not, say so and what you will try.

Never rewrite a whole file with write_file for one change.
