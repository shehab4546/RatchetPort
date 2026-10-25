# SPDX-License-Identifier: GPL-2.0-or-later
"""Quality settings only; input, language and frame-rate preferences stay independent."""
PRESETS = {
    name: dict(internal_resolution=resolution, output_res=output,
               shadow_resolution=shadow, anisotropy=filtering, motion_blur=blur)
    for name, resolution, output, shadow, filtering, blur in (
        ('Low', '720p', '1280x720', '256', '1', 'off'),
        ('Medium', '900p', '1920x1080', '512', '2', 'off'),
        ('High', '1080p', '1920x1080', '1024', '4', 'original'),
        ('Very High', '1440p', '2560x1440', 'original', '8', 'original'),
        ('Ultra', '4K', '3840x2160', 'original', '16', 'original'),
    )
}


def detect(values):
    return next((name for name, settings in PRESETS.items()
                 if all(str(values.get(key)) == value for key, value in settings.items())), 'Custom')
