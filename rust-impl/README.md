# sentinel-manifest (Rust)

Rust implementation of [RFC-001 SovereigntyManifest](../docs/rfcs/RFC-001-sovereignty-manifest.md).

Compatible with the [Python reference implementation](https://github.com/sebastianweiss83/sentinel-kernel) (`sentinel-kernel`).

## Install

```toml
[dependencies]
sentinel-manifest = "0.1"
```

## Usage

```rust
use sentinel_manifest::{SovereigntyManifest, EUJurisdiction, AirGapRequired, AcknowledgedGap};

let report = SovereigntyManifest::new("My Policy v1")
    .add(Box::new(EUJurisdiction::new()))
    .add(Box::new(AirGapRequired::new()))
    .add(Box::new(AcknowledgedGap::new(
        "GitHub Actions",
        "No production-ready EU alternative today",
        "Self-hosted Forgejo",
        "2027-Q2",
    )))
    .check();

println!("Score: {:.0}%", report.overall_score * 100.0);
```

## Examples

```bash
cargo run --example basic
```

## Tests

```bash
cargo test
```

## License

Apache 2.0. Same as the Python reference implementation.
