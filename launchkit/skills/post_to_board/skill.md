# post_to_board

Pick me when: the work goes back to the marketer's board, e.g. "put the sizes on the Tidal card".
Uses: read_card, attach_files, update_status, notion-search, notion-fetch, notion-update-page, notion-create-comment

## Steps

One board is plugged in: the local board (read_card, attach_files, update_status) or Notion (the notion- tools). Use the steps for the one you have.

On the local board:
1. Call read_card to read the card's brief, status and files.
2. Call attach_files with the finished files.
3. Call update_status to move the card to "Ready for review".

On Notion:
1. Call notion-search with the card's name, e.g. "Tidal launch", to find its page. Then call notion-fetch with the page id to read the brief, status and files.
2. Call notion-update-page with command "update_content" and content_updates [{"old_str": ..., "new_str": ...}]: change the Status line to "Status: Ready for review", and add the finished file names to the end of the Files line. Keep the files already there.
3. Call notion-create-comment with the page_id and markdown: a one-line note that lists the new files.

Then tell the marketer what you added and the card's new status.
