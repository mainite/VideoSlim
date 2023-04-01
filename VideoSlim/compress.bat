".\tools\ffmpeg.exe" -i %1 -vn -sn -v 0 -c:a pcm_s16le -f wav pipe:  | ".\tools\neroAacEnc.exe" -ignorelength -lc -br 128000 -if - -of ".\old_atemp.mp4" 
".\tools\x264_32-8bit.exe" --crf 23.5 --preset 8  -I 600 -r 4 -b 3 --me umh -i 1 --scenecut 60 -f 1:1 --qcomp 0.5 --psy-rd 0.3:0 --aq-mode 2 --aq-strength 0.8 -o ".\old_vtemp.mp4" %1
".\tools\mp4box.exe" -add ".\old_vtemp.mp4#trackID=1:name=" -add ".\old_atemp.mp4#trackID=1:name=" -new %2 
del .\old_atemp.mp4 .\old_vtemp.mp4
