# Security

Do not report real credentials, tokens, private model access, account identifiers,
cluster endpoints, customer data, or other secrets in public issues.

Course examples must:

- use placeholders for account, role, cluster, subnet, and registry identifiers;
- avoid public load balancers until authentication and exposure are taught;
- use workload identity rather than static cloud credentials;
- pin and verify model, dataset, package, and container sources;
- treat retrieved documents and model outputs as untrusted data;
- keep runtime adapter loading and arbitrary remote code disabled by default.

For a suspected vulnerability in course code, contact the repository owner
privately before opening a public issue. Replace this paragraph with the actual
private reporting channel before publishing the repository.
