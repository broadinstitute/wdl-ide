version 1.0

workflow example {
  input {
    File in
  }

  call echo as echo_alias {
    input:
      in = in
  }

  output {
    String out = echo_alias.out
  }
}

task echo {
  input {
    File in
  }

  command {
    cat "~{in}" >&2
    exit 1
  }

  runtime {
    docker: "debian:testing-slim"
  }

  output {
    String out = read_string(stdout())
  }
}
