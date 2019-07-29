# Community Collections

Community Collections (CC) is an open-source high-performance computing (HPC) framework which provides a seamless interface between [Lmod](https://lmod.readthedocs.io/en/latest/) and [Singularity containers](https://sylabs.io/singularity/) so that users can download and deploy software in a Singularity container using the elegant module Lmod system. The CC tool is useful for administrators who wish to install or detect both Lmod and Singularity, customize a list of containers from public sources ([Docker Hub](), and [Singularity Hub](https://singularity-hub.org/), and [Syslabs Cloud Library](https://cloud.sylabs.io/library)).

Requirements
------------

1. Linux
2. A root-installed Singularity or else we will install
3. "Development Tools" including the [`gcc`](https://gcc.gnu.org/) compiler
4. `bzip2`
5. `git`
6. `wget`
7. The `cryptsetup` if installing Singularity
8. A kernel with user namespaces if you lack root and wish to use Singularity sandbox containers instead of image files

Installation
------------

You can install a copy of Community Collections by cloning the source code and running a single "refresh" command. This command will first install a [Miniconda](https://docs.conda.io/en/latest/miniconda.html) environment to provide supporting software (more on this later), and then either detect or install Singularity and Lmod.

```
git clone http://github.com/community-collections/community-collections
cd community-collections
./cc refresh
```

What happens when you run "refresh"?
------------------------------------

Each time you run the `./cc refresh` command, it runs the following loop.

1. Install the python environment to `./miniconda` and point the `./cc` executable to use that environment. This provides a consistent python environment.
2. Read the `cc.yaml` file or write the default one.
3. Check for Singularity and Lmod and if they are not registered in `cc.yaml`, install them.