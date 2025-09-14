# Code Quality Report

**Overall Score:** 85/100

## Top Issues

| ID | Severity | Location | Message |
|----|----------|----------|---------|
| PY-CPLX-5ed12b5b9a59 | high | core/video_processor.py:22 | Function 'process_video' has high complexity (cc=33). |
| PY-SEC-2b0791f96540 | high | features/scene_intensity.py:12 | Use of dangerous function 'eval'. |
| PY-CPLX-b8efa0537e7c | high | utils/process_video_and_score.py:115 | Function 'process_video' has high complexity (cc=33). |
| PY-SEC-70ee9d6690bf | high | utils/scene_intensity.py:12 | Use of dangerous function 'eval'. |
| PY-CPLX-7a797b2aebdb | high | utils/youtube_uploader.py:386 | Function 'interactive_analytics' has high complexity (cc=36). |

## Recommendations

- Refactor function in `core/video_processor.py` at line 22 to reduce complexity.
- Address security issue in `features/scene_intensity.py:12` - Use of dangerous function 'eval'..
- Refactor function in `utils/process_video_and_score.py` at line 115 to reduce complexity.
- Address security issue in `utils/scene_intensity.py:12` - Use of dangerous function 'eval'..
- Refactor function in `utils/youtube_uploader.py` at line 386 to reduce complexity.