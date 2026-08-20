{
  description = "build123d Python CAD dev environment (standalone browser viewer)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        # Pin the interpreter. The OCP wheels only ship aarch64-linux builds
        # for cp310-cp313, so we must NOT let uv wander onto Python 3.14+.
        python = pkgs.python313;

        libPath = pkgs.lib.makeLibraryPath [
          pkgs.stdenv.cc.cc.lib # libstdc++.so.6
          pkgs.zlib
          pkgs.libGL
          pkgs.libGLU
          pkgs.expat # libexpat.so.1
          pkgs.libx11 # libX11.so.6
          pkgs.libxrender # libXrender.so.1
          pkgs.fontconfig.lib # libfontconfig.so.1 (OCP text/rendering)
          pkgs.freetype # libfreetype.so.6
          pkgs.glib.out # libglib/libgthread
        ];
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            python
            pkgs.uv
            pkgs.go-task # `task` — canonical entry points (see Taskfile.yml)
          ];

          env = {
            # Never let uv download its own interpreter; always use the pinned one.
            UV_PYTHON_DOWNLOADS = "never";
            UV_PYTHON = "${python}/bin/python3.13";
            LD_LIBRARY_PATH = libPath;
          };

          shellHook = ''
            # A stale .venv built with a different Python (e.g. a previous uv 3.14)
            # is the classic cause of "no wheel for this platform". Rebuild it.
            if [ -x .venv/bin/python ]; then
              venv_py="$(.venv/bin/python -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null || echo none)"
              if [ "$venv_py" != "3.13" ]; then
                echo "Recreating .venv (was Python $venv_py, need 3.13)"
                rm -rf .venv
              fi
            fi

            if uv sync; then
              source .venv/bin/activate
              echo "build123d dev environment ready"
              echo "Python:      $(python --version)"

              echo ""
              echo "Viewer (browser, works in this VM):  task viewer   -> http://127.0.0.1:3939"
              echo "Then build the case:                 task build"
              echo "Variants:                            task snapfit | task xiaofit"
            else
              echo "uv sync FAILED — see error above."
            fi
          '';
        };
      });
}
