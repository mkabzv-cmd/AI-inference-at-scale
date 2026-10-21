# Authentication and exposure release gate

The checked-in course workload has no public route. Its Service is `ClusterIP`
and a default-deny NetworkPolicy permits ingress only from a specifically
labeled gateway Pod in a specifically labeled namespace. This is network
segmentation, not user authentication.

Before exposing restricted content:

1. Select the authentication mechanism native to the intended caller and
   platform. For AWS service callers, a common option is a private API endpoint
   using AWS IAM/SigV4 plus action-level IAM authorization. For human users,
   use the organization's supported identity gateway; do not invent a bearer
   token verifier for this course.
2. Create the origin without restricted model/data content.
3. Attach authentication and authorization.
4. From an anonymous client, require an identifiable 401/403 from the gate.
   A connection failure or missing object is not proof of authentication.
5. From an authenticated but unauthorized principal, require denial.
6. From one authorized principal, verify only the permitted action/tenant.
7. Only after denial is proved, attach restricted artifacts or data.
8. Re-run anonymous denial after every gateway/policy change.

If the real identity integration is unavailable, remain private and fail
closed. Do not publish a route with decorative header checks or a shared secret
invented for the tutorial.
