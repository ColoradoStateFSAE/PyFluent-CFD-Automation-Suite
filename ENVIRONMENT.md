# Fluent Environment Configuration
Required environment variables for PyFluent.

## Windows
Set:
- AWP_ROOT = path to v251
- ANSYS_FLUENT_DIR = v251\fluent

Add to PATH:
- fluent\bin
- Tcl\bin
- MPI\bin
- Framework\bin\Win64

Test:
```
fluent 3ddp -v
```

## Linux
Add to ~/.bashrc:
```
export AWP_ROOT="/usr/ansys_inc/v251"
export ANSYS_FLUENT_DIR="/usr/ansys_inc/v251/fluent"
export PATH="$ANSYS_FLUENT_DIR/bin:$PATH"
export LD_LIBRARY_PATH="/usr/ansys_inc/v251/fluent/lib:$LD_LIBRARY_PATH"
```

Test:
```
fluent 3ddp -g
```

