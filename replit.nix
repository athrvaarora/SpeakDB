{pkgs}: {
  deps = [
    pkgs.unixODBC
    pkgs.postgresql
    pkgs.openssl
  ];
}
