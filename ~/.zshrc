update_content() {
  rsync -av --delete --exclude ".obsidian/" --exclude "**/.DS_Store" \
    "/Users/jaehyeonlee/Library/Mobile Documents/iCloud~md~obsidian/Documents/j-h-prototype-5/" \
    "/Users/jaehyeonlee/Desktop/j-h/_staging/"

  /usr/bin/python3 "/Users/jaehyeonlee/Desktop/j-h/fix_links.py"

  rsync -av --delete \
    "/Users/jaehyeonlee/Desktop/j-h/_staging/" \
    "/Users/jaehyeonlee/Desktop/j-h/content/"

  echo "update-content: done"
}