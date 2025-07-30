{
  description = "My project dev shell (Python + Black)";

  inputs = { nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable"; };

  outputs = { nixpkgs, ... }:
    let
      system = "x86_64-linux"; # needs to be adjusted for M processors to "aarch64-darwin"
      pkgs = import nixpkgs { inherit system; };
      python = pkgs.python312; # python version
    in {
      devShells."${system}".default = pkgs.mkShell {
        buildInputs = [
          # a single python wrapper that includes black, pytest, isort
          (python.withPackages
            (ps: with ps; [ black pytest isort pylint mypy pip ]))
          # any other CLI tools
          pkgs.direnv
          pkgs.jdk21_headless
        ];
        shellHook = ''
          # auto-allow direnv if installed
          command -v direnv >/dev/null && direnv allow || true
          python -m venv .venv
          source .venv/bin/activate
          pip install -r requirements.txt
          '';
      };
    };
}