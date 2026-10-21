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

For a suspected vulnerability in course code, use GitHub's private
vulnerability-reporting flow from the repository's **Security** tab when it is
available. Otherwise, contact the maintainer privately through the contact
method on the maintainer's GitHub profile. Do not include exploit details,
credentials, private infrastructure identifiers, or customer data in a public
issue.
