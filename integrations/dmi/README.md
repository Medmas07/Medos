# DMI / HIS Integration

Reserved for hospital-specific adapters that map and normalize legacy DMI/HIS representations into a selected canonical clinical model:

```text
Legacy DMI / HIS -> hospital-specific adapter -> mapping / normalization -> canonical model
```

No universal DMI, canonical model, mapping, fixture, or adapter implementation is assumed. Add `adapters/` or non-sensitive `fixtures/` only for a concrete hospital integration.
