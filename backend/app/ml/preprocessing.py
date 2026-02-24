import os
import sys
import platform
import shutil
from pathlib import Path
import torchaudio


def patch_torchaudio():
    if not hasattr(torchaudio, 'set_audio_backend'):
        def _dummy_set_audio_backend(backend):
            """Dummy function to satisfy speechbrain compatibility"""
            pass
        torchaudio.set_audio_backend = _dummy_set_audio_backend

    if not hasattr(torchaudio, 'list_audio_backends'):
        def _dummy_list_audio_backends():
            """Dummy function to satisfy speechbrain compatibility"""
            return ['soundfile']
        torchaudio.list_audio_backends = _dummy_list_audio_backends

    if not hasattr(torchaudio, 'get_audio_backend'):
        def _dummy_get_audio_backend():
            """Dummy function to satisfy speechbrain compatibility"""
            return 'soundfile'
        torchaudio.get_audio_backend = _dummy_get_audio_backend


def patch_os_symlink():
    if platform.system() == "Windows":
        _original_symlink = os.symlink

        def _patched_symlink(src, dst, target_is_directory=False):
            """On Windows, copy files instead of creating symlinks"""
            try:
                return _original_symlink(src, dst, target_is_directory=target_is_directory)
            except (OSError, PermissionError) as e:
                if "1314" in str(e) or "privilege" in str(e).lower():
                    try:
                        src_path = Path(src)
                        dst_path = Path(dst)
                        dst_path.parent.mkdir(parents=True, exist_ok=True)

                        if src_path.is_dir() and target_is_directory:
                            shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                        else:
                            shutil.copy2(src_path, dst_path)
                        return None
                    except Exception as copy_err:
                        raise e from copy_err
                else:
                    raise

        os.symlink = _patched_symlink
