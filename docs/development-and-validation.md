# Development And Validation

## Package Identity

- Package name: `comfyui-geekatplay-video-editor-suite`
- Display name: `Geekatplay Video Editor Suite`
- Repository: `https://github.com/GeekatplayStudio/video-editor-suite`

## Validation Commands

### Python Syntax

```powershell
py -3 -m compileall "O:\ComfyUI\custom_nodes\ComfyUI-Geekatplay-VideoEditorSuite"
```

### Portable ComfyUI Runtime

If you are running ComfyUI portable on Windows, the relevant interpreter may be `python_embeded\python.exe` at the drive root used by your install.

### Runtime Smoke Tests

The editing and export nodes were smoke-tested with synthetic `IMAGE` and `AUDIO` tensors under the ComfyUI runtime environment. The export test produced a valid MP4 with one video stream and one audio stream.

## Notes For Contributors

- Keep node additions additive rather than replacing existing workflows.
- Preserve `GUIDE_DATA` for guide socket compatibility with copied example workflows.
- Favor focused validation after each edit slice instead of broad repo-wide changes.
