Require bwrap
Type@0 exec bash
Enter
Type@0 exec bwrap --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp --tmpfs /home/user --dir /home/user/.cache --bind /home/josiah/.cache /home/user/.cache --setenv HOME /home/user --chdir /home/user --file 11 /home/user/.config/euporie/config.toml  --file 12 /home/user/.local/share/euporie/state.toml --file 13 /home/user/.local/share/jupyter/kernels/python3/kernel.json  --file 14 /home/user/.local/share/jupyter/kernels/pypy/kernel.json /bin/zsh 11< <(printf '[notebook]\nbackground_pattern = 9\nbackground_character = "░"\nmax_notebook_width = 50\nshow_side_bar = false\n\n[console]\nmouse_support = true') 12< <(printf '[notebook]\ntip_offset = 105') 13< <(printf '{"argv": ["uvx","--with","ipywidgets","--with","numpy","--with","pandas","--with","jinja2","--with","matplotlib","--with","tdqm","--with","rich","--with","ipykernel","python3.14","-m","ipykernel_launcher","-f","{connection_file}"],"display_name": "Python 3 (ipykernel)","language": "python","kernel_protocol_version": "5.5"}') 14< <(printf '{"argv": ["uvx","--with","ipykernel","pypy3","-m","ipykernel_launcher","-f","{connection_file}"],"display_name": "PyPy","language": "python","kernel_protocol_version": "5.5"}')
Enter
Ctrl+L
Wait+line / ~  /

