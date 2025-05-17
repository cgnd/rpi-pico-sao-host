# Contributing

Due to license restrictions for some of the 3D models embedded in this design, the [CGND KiCad Library](https://github.com/cgnd/cgnd-kicad-lib/) submodule is currently a private repository which cannot be open-sourced without violating the license terms. In addition, this design uses database libraries managed by the <https://cgnd-oshw.aligni.com> Aligni PLM instance.

Without access to the source libraries, it is difficult for anyone who is not a member of the Common Ground Electronics organization to contribute any major design changes back into this project.

However, there are still many ways you can contribute! Since this design is open-source, you are encouraged to use and modify it to make your own boards.

If you find any issues with this design or have suggestions for how it can be improved in a future version, please [create an issue](https://github.com/cgnd/rpi-pico-sao-host/issues/new) or [start a discussion](https://github.com/cgnd/rpi-pico-sao-host/discussions/new/choose) on GitHub.

## Checking out the design

Clone the repository using Git.

```sh
git clone https://github.com/cgnd/rpi-pico-sao-host.git
git submodule update --init
```

A couple tools need to be installed first in order to set up the project for development:

* [git](https://git-scm.com/)
* [uv](https://docs.astral.sh/uv/)

Once these tools are installed, install the python dependencies via `uv`:

```sh
cd rpi-pico-sao-host/
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

This will install the [Invoke](https://www.pyinvoke.org/) task runner which provides commands to manage the project.

## Running design checks

The `check` task runs ERC & DRC checks against the schematic and PCB respectively:

```sh
cd rpi-pico-sao-host/
inv check
```

## Generating release files

The `release` task generates the release files for manufacturing (it will automatically run the `check` task before generating the release files):

```sh
cd rpi-pico-sao-host/
inv release
```

The `clean` task will remove the generated files:

```sh
inv clean
```

To print the full list of Invoke tasks available, run the following command:

```sh
inv --list
```
