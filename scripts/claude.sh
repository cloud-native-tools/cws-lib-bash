function claude_dev() {
  claude --permission-mode acceptEdits
}

function claude_yolo() {
  claude --dangerously-skip-permissions || claude --permission-mode bypassPermissions
}
