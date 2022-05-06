function mov2gif() {
  ffmpeg -i "$1" -pix_fmt rgb24 -r 10 "$2"
}
function optimize_gif() {
  gifsicle --optimize=3 --delay=3 "$1" -o "$2"
}
