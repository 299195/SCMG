# Architecture

SCMG separates the authenticated user request from external task material. The
bridge hashes both channels, assigns an origin identifier, and writes policy
events to a hash-chained audit log.

At memory-write time, the policy splits Markdown into claim-sized units. Plain
facts remain attributed to their source. External standing rules, security
bypasses, and high-risk instructions are quarantined. External destinations are
replaced unless the current request directly authorizes the action and target.

After a memory tool returns, the plugin snapshots managed Markdown files and
asks the bridge to evaluate the actual persisted content. This catches memory
changes made through a path that bypassed the write preflight.

Before reuse, SCMG projects every managed memory file through the current
policy, filters candidate claims, and renders an attributed context. Native
memory reads are blocked during this phase so the agent uses the verified
projection.

Sensitive tools are checked against the current user request. The included gate
covers scheduled actions, message destinations, protected bootstrap files, and
obvious network-write commands. A deployment should extend this mapping for its
own tools and sinks.

The OpenClaw plugin fails closed at the affected hook when the bridge is
unavailable or returns an invalid response.
