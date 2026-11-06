{
  description = "duality_wave - parametric case for a split, hand-wired, low-profile keyboard (build123d)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        # Pin the interpreter. The OCP wheels ship builds for cp310-cp313 only.
        python = pkgs.python313;
        # build123d is not packaged in nixpkgs. It comes from PyPI (pinned by uv.lock).
        # The OCP wheels need these shared libraries at run time.
        runtimeLibs = with pkgs; [
          stdenv.cc.cc.lib
          libGL
          libGLU
          libglvnd
          libx11
          libxext
          libxrender
          fontconfig
          freetype
          glib.out
          zlib
          expat
          libpng
          bzip2
          brotli
        ];
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            python
            pkgs.uv
            pkgs.go-task
            pkgs.ergogen
          ];
          env = {
            # Never let uv download its own interpreter. Always use the pinned one.
            UV_PYTHON_DOWNLOADS = "never";
            UV_PYTHON = "${python}/bin/python3";
            # Fixed font so engraved labels look the same on every machine.
            FONTCONFIG_FILE = pkgs.writeText "fonts.conf" ''
              <?xml version="1.0"?>
              <!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
              <fontconfig>
                <dir>${pkgs.dejavu_fonts}</dir>
                <cachedir>/tmp/fontconfig-cache</cachedir>
              </fontconfig>
            '';
          } // pkgs.lib.optionalAttrs pkgs.stdenv.hostPlatform.isLinux {
            LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath runtimeLibs;
          };
          shellHook = ''
            # Always use this project's .venv, even inside a shell that was started for another project.
            export UV_PROJECT_ENVIRONMENT="$PWD/.venv"
            # A venv built with another Python minor version has no matching wheels. Rebuild it.
            if [ -x .venv/bin/python ]; then
              venv_py="$(.venv/bin/python -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null || echo none)"
              if [ "$venv_py" != "3.13" ]; then
                echo "Recreating .venv (was Python $venv_py, need 3.13)"
                rm -rf .venv
              fi
            fi
            if ! uv sync --frozen --quiet; then
              echo "uv sync FAILED - see the error above."
            fi
            export PATH="$PWD/.venv/bin:$PATH"
            echo "duality_wave dev shell"
            echo "  task check    fast checks (lock file, lint, fast tests)"
            echo "  task test     check, then all tests in parallel"
            echo "  task viewer   start the OCP viewer, then open http://127.0.0.1:3939"
            echo "  task build    build the case and export STEP files to build/step"
            echo "  task compact  build the compact variant"
            echo "  task update   upgrade the Python packages in uv.lock"
          '';
        };

        formatter = pkgs.nixfmt-tree;
      });
}
