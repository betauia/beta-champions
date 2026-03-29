{
  description = "Dev environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
  };

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-darwin" ];
      forAllSystems = f: nixpkgs.lib.genAttrs supportedSystems (system:
        let pkgs = import nixpkgs { inherit system; };
        in f pkgs system
      );
    in
    {
      devShells = forAllSystems (pkgs: system: {
        default = pkgs.mkShell {
          packages = with pkgs; [
            python313
            uv
            kubectl
            minikube
          ];

          shellHook = ''
            echo "🚀 Hei sjef! Hva skal det være i dag?"
            echo "System: ${system}"
          '';
        };
      });
    };
}

