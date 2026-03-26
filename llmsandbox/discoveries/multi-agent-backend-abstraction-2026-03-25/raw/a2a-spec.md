[ Skip to content ](https://a2a-protocol.org/latest/specification/#agent2agent-a2a-protocol-specification)
**A2A: The Agent2Agent Protocol**! [ Enroll for free ](https://goo.gle/dlai-a2a)
[ ![logo](https://a2a-protocol.org/latest/assets/a2a-logo-white.svg) ](https://a2a-protocol.org/latest/ "A2A Protocol")
A2A Protocol 
Overview 
Type to start searching
[ a2aproject/A2A 
  * v1.0.0
  * 22.8k
  * 2.3k

](https://github.com/a2aproject/A2A "Go to repository")
[ ![logo](https://a2a-protocol.org/latest/assets/a2a-logo-white.svg) ](https://a2a-protocol.org/latest/ "A2A Protocol") A2A Protocol 
[ a2aproject/A2A 
  * v1.0.0
  * 22.8k
  * 2.3k

](https://github.com/a2aproject/A2A "Go to repository")
  * [ Home  ](https://a2a-protocol.org/latest/)
  * [ ?? Announcing Version 1.0  ](https://a2a-protocol.org/latest/announcing-1.0/)
  * Documentation 
    * [ What is A2A?  ](https://a2a-protocol.org/latest/topics/what-is-a2a/)
    * [ Core Concepts  ](https://a2a-protocol.org/latest/topics/key-concepts/)
    * [ Agent Discovery  ](https://a2a-protocol.org/latest/topics/agent-discovery/)
    * [ Enterprise Features  ](https://a2a-protocol.org/latest/topics/enterprise-ready/)
    * [ Life of a Task  ](https://a2a-protocol.org/latest/topics/life-of-a-task/)
    * [ Extensions  ](https://a2a-protocol.org/latest/topics/extensions/)
    * [ Streaming & Asynchronous Operations  ](https://a2a-protocol.org/latest/topics/streaming-and-async/)
    * [ A2A and MCP  ](https://a2a-protocol.org/latest/topics/a2a-and-mcp/)
  * [ Tutorials and Samples  ](https://a2a-protocol.org/latest/tutorials/)
    * Quickstart (Python) 
      * [ Introduction  ](https://a2a-protocol.org/latest/tutorials/python/1-introduction/)
      * [ Setup  ](https://a2a-protocol.org/latest/tutorials/python/2-setup/)
      * [ Agent Skills & Agent Card  ](https://a2a-protocol.org/latest/tutorials/python/3-agent-skills-and-card/)
      * [ Agent Executor  ](https://a2a-protocol.org/latest/tutorials/python/4-agent-executor/)
      * [ Start Server  ](https://a2a-protocol.org/latest/tutorials/python/5-start-server/)
      * [ Interact with Server  ](https://a2a-protocol.org/latest/tutorials/python/6-interact-with-server/)
      * [ Streaming & Multiturn  ](https://a2a-protocol.org/latest/tutorials/python/7-streaming-and-multiturn/)
      * [ Next Steps  ](https://a2a-protocol.org/latest/tutorials/python/8-next-steps/)
    * [ DeepLearning.AI Course  ](https://goo.gle/dlai-a2a)
  * Specification 
    * Overview  [ Overview  ](https://a2a-protocol.org/latest/specification/)
      * [ 1. Introduction  ](https://a2a-protocol.org/latest/specification/#1-introduction)
        * [ 1.1. Key Goals of A2A  ](https://a2a-protocol.org/latest/specification/#11-key-goals-of-a2a)
        * [ 1.2. Guiding Principles  ](https://a2a-protocol.org/latest/specification/#12-guiding-principles)
        * [ 1.3. Specification Structure  ](https://a2a-protocol.org/latest/specification/#13-specification-structure)
        * [ 1.4 Normative Content  ](https://a2a-protocol.org/latest/specification/#14-normative-content)
      * [ 2. Terminology  ](https://a2a-protocol.org/latest/specification/#2-terminology)
        * [ 2.1. Requirements Language  ](https://a2a-protocol.org/latest/specification/#21-requirements-language)
        * [ 2.2. Core Concepts  ](https://a2a-protocol.org/latest/specification/#22-core-concepts)
      * [ 3. A2A Protocol Operations  ](https://a2a-protocol.org/latest/specification/#3-a2a-protocol-operations)
        * [ 3.1. Core Operations  ](https://a2a-protocol.org/latest/specification/#31-core-operations)
          * [ 3.1.1. Send Message  ](https://a2a-protocol.org/latest/specification/#311-send-message)
          * [ 3.1.2. Send Streaming Message  ](https://a2a-protocol.org/latest/specification/#312-send-streaming-message)
          * [ 3.1.3. Get Task  ](https://a2a-protocol.org/latest/specification/#313-get-task)
          * [ 3.1.4. List Tasks  ](https://a2a-protocol.org/latest/specification/#314-list-tasks)
          * [ 3.1.5. Cancel Task  ](https://a2a-protocol.org/latest/specification/#315-cancel-task)
          * [ 3.1.6. Subscribe to Task  ](https://a2a-protocol.org/latest/specification/#316-subscribe-to-task)
          * [ 3.1.7. Create Push Notification Config  ](https://a2a-protocol.org/latest/specification/#317-create-push-notification-config)
          * [ 3.1.8. Get Push Notification Config  ](https://a2a-protocol.org/latest/specification/#318-get-push-notification-config)
          * [ 3.1.9. List Push Notification Configs  ](https://a2a-protocol.org/latest/specification/#319-list-push-notification-configs)
          * [ 3.1.10. Delete Push Notification Config  ](https://a2a-protocol.org/latest/specification/#3110-delete-push-notification-config)
          * [ 3.1.11. Get Extended Agent Card  ](https://a2a-protocol.org/latest/specification/#3111-get-extended-agent-card)
        * [ 3.2. Operation Parameter Objects  ](https://a2a-protocol.org/latest/specification/#32-operation-parameter-objects)
          * [ 3.2.1. SendMessageRequest  ](https://a2a-protocol.org/latest/specification/#321-sendmessagerequest)
          * [ 3.2.2. SendMessageConfiguration  ](https://a2a-protocol.org/latest/specification/#322-sendmessageconfiguration)
          * [ 3.2.3. Stream Response  ](https://a2a-protocol.org/latest/specification/#323-stream-response)
          * [ 3.2.4. History Length Semantics  ](https://a2a-protocol.org/latest/specification/#324-history-length-semantics)
          * [ 3.2.5. Metadata  ](https://a2a-protocol.org/latest/specification/#325-metadata)
          * [ 3.2.6 Service Parameters  ](https://a2a-protocol.org/latest/specification/#326-service-parameters)
        * [ 3.3. Operation Semantics  ](https://a2a-protocol.org/latest/specification/#33-operation-semantics)
          * [ 3.3.1. Idempotency  ](https://a2a-protocol.org/latest/specification/#331-idempotency)
          * [ 3.3.2. Error Handling  ](https://a2a-protocol.org/latest/specification/#332-error-handling)
          * [ 3.3.3. Asynchronous Processing  ](https://a2a-protocol.org/latest/specification/#333-asynchronous-processing)
          * [ 3.3.4. Capability Validation  ](https://a2a-protocol.org/latest/specification/#334-capability-validation)
        * [ 3.4. Multi-Turn Interactions  ](https://a2a-protocol.org/latest/specification/#34-multi-turn-interactions)
          * [ 3.4.1. Context Identifier Semantics  ](https://a2a-protocol.org/latest/specification/#341-context-identifier-semantics)
          * [ 3.4.2. Task Identifier Semantics  ](https://a2a-protocol.org/latest/specification/#342-task-identifier-semantics)
          * [ 3.4.3. Multi-Turn Conversation Patterns  ](https://a2a-protocol.org/latest/specification/#343-multi-turn-conversation-patterns)
        * [ 3.5. Task Update Delivery Mechanisms  ](https://a2a-protocol.org/latest/specification/#35-task-update-delivery-mechanisms)
          * [ 3.5.1. Overview of Update Mechanisms  ](https://a2a-protocol.org/latest/specification/#351-overview-of-update-mechanisms)
          * [ 3.5.2. Streaming Event Delivery  ](https://a2a-protocol.org/latest/specification/#352-streaming-event-delivery)
          * [ 3.5.3. Push Notification Delivery  ](https://a2a-protocol.org/latest/specification/#353-push-notification-delivery)
        * [ 3.6 Versioning  ](https://a2a-protocol.org/latest/specification/#36-versioning)
          * [ 3.6.1 Client Responsibilities  ](https://a2a-protocol.org/latest/specification/#361-client-responsibilities)
          * [ 3.6.2 Server Responsibilities  ](https://a2a-protocol.org/latest/specification/#362-server-responsibilities)
          * [ 3.6.3 Tooling support  ](https://a2a-protocol.org/latest/specification/#363-tooling-support)
        * [ 3.7 Messages and Artifacts  ](https://a2a-protocol.org/latest/specification/#37-messages-and-artifacts)
      * [ 4. Protocol Data Model  ](https://a2a-protocol.org/latest/specification/#4-protocol-data-model)
        * [ 4.1. Core Objects  ](https://a2a-protocol.org/latest/specification/#41-core-objects)
          * [ 4.1.1. Task  ](https://a2a-protocol.org/latest/specification/#411-task)
          * [ 4.1.2. TaskStatus  ](https://a2a-protocol.org/latest/specification/#412-taskstatus)
          * [ 4.1.3. TaskState  ](https://a2a-protocol.org/latest/specification/#413-taskstate)
          * [ 4.1.4. Message  ](https://a2a-protocol.org/latest/specification/#414-message)
          * [ 4.1.5. Role  ](https://a2a-protocol.org/latest/specification/#415-role)
          * [ 4.1.6. Part  ](https://a2a-protocol.org/latest/specification/#416-part)
          * [ 4.1.7. Artifact  ](https://a2a-protocol.org/latest/specification/#417-artifact)
        * [ 4.2. Streaming Events  ](https://a2a-protocol.org/latest/specification/#42-streaming-events)
          * [ 4.2.1. TaskStatusUpdateEvent  ](https://a2a-protocol.org/latest/specification/#421-taskstatusupdateevent)
          * [ 4.2.2. TaskArtifactUpdateEvent  ](https://a2a-protocol.org/latest/specification/#422-taskartifactupdateevent)
        * [ 4.3. Push Notification Objects  ](https://a2a-protocol.org/latest/specification/#43-push-notification-objects)
          * [ 4.3.1. PushNotificationConfig  ](https://a2a-protocol.org/latest/specification/#431-pushnotificationconfig)
          * [ 4.3.2. AuthenticationInfo  ](https://a2a-protocol.org/latest/specification/#432-authenticationinfo)
          * [ 4.3.3. Push Notification Payload  ](https://a2a-protocol.org/latest/specification/#433-push-notification-payload)
        * [ 4.4. Agent Discovery Objects  ](https://a2a-protocol.org/latest/specification/#44-agent-discovery-objects)
          * [ 4.4.1. AgentCard  ](https://a2a-protocol.org/latest/specification/#441-agentcard)
          * [ 4.4.2. AgentProvider  ](https://a2a-protocol.org/latest/specification/#442-agentprovider)
          * [ 4.4.3. AgentCapabilities  ](https://a2a-protocol.org/latest/specification/#443-agentcapabilities)
          * [ 4.4.4. AgentExtension  ](https://a2a-protocol.org/latest/specification/#444-agentextension)
          * [ 4.4.5. AgentSkill  ](https://a2a-protocol.org/latest/specification/#445-agentskill)
          * [ 4.4.6. AgentInterface  ](https://a2a-protocol.org/latest/specification/#446-agentinterface)
          * [ 4.4.7. AgentCardSignature  ](https://a2a-protocol.org/latest/specification/#447-agentcardsignature)
        * [ 4.5. Security Objects  ](https://a2a-protocol.org/latest/specification/#45-security-objects)
          * [ 4.5.1. SecurityScheme  ](https://a2a-protocol.org/latest/specification/#451-securityscheme)
          * [ 4.5.2. APIKeySecurityScheme  ](https://a2a-protocol.org/latest/specification/#452-apikeysecurityscheme)
          * [ 4.5.3. HTTPAuthSecurityScheme  ](https://a2a-protocol.org/latest/specification/#453-httpauthsecurityscheme)
          * [ 4.5.4. OAuth2SecurityScheme  ](https://a2a-protocol.org/latest/specification/#454-oauth2securityscheme)
          * [ 4.5.5. OpenIdConnectSecurityScheme  ](https://a2a-protocol.org/latest/specification/#455-openidconnectsecurityscheme)
          * [ 4.5.6. MutualTlsSecurityScheme  ](https://a2a-protocol.org/latest/specification/#456-mutualtlssecurityscheme)
          * [ 4.5.7. OAuthFlows  ](https://a2a-protocol.org/latest/specification/#457-oauthflows)
          * [ 4.5.8. AuthorizationCodeOAuthFlow  ](https://a2a-protocol.org/latest/specification/#458-authorizationcodeoauthflow)
          * [ 4.5.9. ClientCredentialsOAuthFlow  ](https://a2a-protocol.org/latest/specification/#459-clientcredentialsoauthflow)
          * [ 4.5.10. DeviceCodeOAuthFlow  ](https://a2a-protocol.org/latest/specification/#4510-devicecodeoauthflow)
        * [ 4.6. Extensions  ](https://a2a-protocol.org/latest/specification/#46-extensions)
          * [ 4.6.1. Extension Declaration  ](https://a2a-protocol.org/latest/specification/#461-extension-declaration)
          * [ 4.6.2. Extensions Points  ](https://a2a-protocol.org/latest/specification/#462-extensions-points)
          * [ 4.6.3. Extension Versioning and Compatibility  ](https://a2a-protocol.org/latest/specification/#463-extension-versioning-and-compatibility)
      * [ 5. Protocol Binding Requirements and Interoperability  ](https://a2a-protocol.org/latest/specification/#5-protocol-binding-requirements-and-interoperability)
        * [ 5.1. Functional Equivalence Requirements  ](https://a2a-protocol.org/latest/specification/#51-functional-equivalence-requirements)
        * [ 5.2. Protocol Selection and Negotiation  ](https://a2a-protocol.org/latest/specification/#52-protocol-selection-and-negotiation)
        * [ 5.3. Method Mapping Reference  ](https://a2a-protocol.org/latest/specification/#53-method-mapping-reference)
        * [ 5.4. Error Code Mappings  ](https://a2a-protocol.org/latest/specification/#54-error-code-mappings)
        * [ 5.5. JSON Field Naming Convention  ](https://a2a-protocol.org/latest/specification/#55-json-field-naming-convention)
        * [ 5.6. Data Type Conventions  ](https://a2a-protocol.org/latest/specification/#56-data-type-conventions)
          * [ 5.6.1. Timestamps  ](https://a2a-protocol.org/latest/specification/#561-timestamps)
        * [ 5.7. Field Presence and Optionality  ](https://a2a-protocol.org/latest/specification/#57-field-presence-and-optionality)
      * [ 6. Common Workflows & Examples  ](https://a2a-protocol.org/latest/specification/#6-common-workflows-examples)
        * [ 6.1. Basic Task Execution  ](https://a2a-protocol.org/latest/specification/#61-basic-task-execution)
        * [ 6.2. Streaming Task Execution  ](https://a2a-protocol.org/latest/specification/#62-streaming-task-execution)
        * [ 6.3. Multi-Turn Interaction  ](https://a2a-protocol.org/latest/specification/#63-multi-turn-interaction)
        * [ 6.4. Version Negotiation Error  ](https://a2a-protocol.org/latest/specification/#64-version-negotiation-error)
        * [ 6.5. Task Listing and Management  ](https://a2a-protocol.org/latest/specification/#65-task-listing-and-management)
          * [ Request: All tasks from a specific context  ](https://a2a-protocol.org/latest/specification/#request-all-tasks-from-a-specific-context)
          * [ Request: All working tasks across all contexts  ](https://a2a-protocol.org/latest/specification/#request-all-working-tasks-across-all-contexts)
          * [ Pagination Example  ](https://a2a-protocol.org/latest/specification/#pagination-example)
          * [ Validation Error Example  ](https://a2a-protocol.org/latest/specification/#validation-error-example)
        * [ 6.6. Push Notification Setup and Usage  ](https://a2a-protocol.org/latest/specification/#66-push-notification-setup-and-usage)
        * [ 6.7. File Exchange (Upload and Download)  ](https://a2a-protocol.org/latest/specification/#67-file-exchange-upload-and-download)
        * [ 6.8. Structured Data Exchange  ](https://a2a-protocol.org/latest/specification/#68-structured-data-exchange)
        * [ 6.9. Fetching Authenticated Extended Agent Card  ](https://a2a-protocol.org/latest/specification/#69-fetching-authenticated-extended-agent-card)
        * [ Step 2: Client obtains credentials (out-of-band OAuth 2.0 flow)  ](https://a2a-protocol.org/latest/specification/#step-2-client-obtains-credentials-out-of-band-oauth-20-flow)
        * [ Step 3: Client fetches authenticated extended Agent Card  ](https://a2a-protocol.org/latest/specification/#step-3-client-fetches-authenticated-extended-agent-card)
      * [ 7. Authentication and Authorization  ](https://a2a-protocol.org/latest/specification/#7-authentication-and-authorization)
        * [ 7.1. Protocol Security  ](https://a2a-protocol.org/latest/specification/#71-protocol-security)
        * [ 7.2. Server Identity Verification  ](https://a2a-protocol.org/latest/specification/#72-server-identity-verification)
        * [ 7.3. Client Authentication Process  ](https://a2a-protocol.org/latest/specification/#73-client-authentication-process)
        * [ 7.4. Server Authentication Responsibilities  ](https://a2a-protocol.org/latest/specification/#74-server-authentication-responsibilities)
        * [ 7.5. Server Authorization Responsibilities  ](https://a2a-protocol.org/latest/specification/#75-server-authorization-responsibilities)
        * [ 7.6. In-Task Authorization  ](https://a2a-protocol.org/latest/specification/#76-in-task-authorization)
          * [ 7.6.1 In-Task Authorization Agent Responsibilities  ](https://a2a-protocol.org/latest/specification/#761-in-task-authorization-agent-responsibilities)
          * [ 7.6.2 In-Task Authorization Client Responsibilities  ](https://a2a-protocol.org/latest/specification/#762-in-task-authorization-client-responsibilities)
          * [ 7.6.3 In-Task Authorization Security Considerations  ](https://a2a-protocol.org/latest/specification/#763-in-task-authorization-security-considerations)
      * [ 8. Agent Discovery: The Agent Card  ](https://a2a-protocol.org/latest/specification/#8-agent-discovery-the-agent-card)
        * [ 8.1. Purpose  ](https://a2a-protocol.org/latest/specification/#81-purpose)
        * [ 8.2. Discovery Mechanisms  ](https://a2a-protocol.org/latest/specification/#82-discovery-mechanisms)
        * [ 8.3. Protocol Declaration Requirements  ](https://a2a-protocol.org/latest/specification/#83-protocol-declaration-requirements)
          * [ 8.3.1. Supported Interfaces Declaration  ](https://a2a-protocol.org/latest/specification/#831-supported-interfaces-declaration)
          * [ 8.3.2. Client Protocol Selection  ](https://a2a-protocol.org/latest/specification/#832-client-protocol-selection)
        * [ 8.4. Agent Card Signing  ](https://a2a-protocol.org/latest/specification/#84-agent-card-signing)
          * [ 8.4.1. Canonicalization Requirements  ](https://a2a-protocol.org/latest/specification/#841-canonicalization-requirements)
          * [ 8.4.2. Signature Format  ](https://a2a-protocol.org/latest/specification/#842-signature-format)
          * [ 8.4.3. Signature Verification  ](https://a2a-protocol.org/latest/specification/#843-signature-verification)
        * [ 8.5. Sample Agent Card  ](https://a2a-protocol.org/latest/specification/#85-sample-agent-card)
        * [ 8.6. Caching  ](https://a2a-protocol.org/latest/specification/#86-caching)
          * [ 8.6.1. Server Requirements  ](https://a2a-protocol.org/latest/specification/#861-server-requirements)
          * [ 8.6.2. Client Requirements  ](https://a2a-protocol.org/latest/specification/#862-client-requirements)
      * [ 9. JSON-RPC Protocol Binding  ](https://a2a-protocol.org/latest/specification/#9-json-rpc-protocol-binding)
        * [ 9.1. Protocol Requirements  ](https://a2a-protocol.org/latest/specification/#91-protocol-requirements)
        * [ 9.2. Service Parameter Transmission  ](https://a2a-protocol.org/latest/specification/#92-service-parameter-transmission)
        * [ 9.3. Base Request Structure  ](https://a2a-protocol.org/latest/specification/#93-base-request-structure)
        * [ 9.4. Core Methods  ](https://a2a-protocol.org/latest/specification/#94-core-methods)
          * [ 9.4.1. SendMessage  ](https://a2a-protocol.org/latest/specification/#941-sendmessage)
          * [ 9.4.2. SendStreamingMessage  ](https://a2a-protocol.org/latest/specification/#942-sendstreamingmessage)
          * [ 9.4.3. GetTask  ](https://a2a-protocol.org/latest/specification/#943-gettask)
          * [ 9.4.4. ListTasks  ](https://a2a-protocol.org/latest/specification/#944-listtasks)
          * [ 9.4.5. CancelTask  ](https://a2a-protocol.org/latest/specification/#945-canceltask)
          * [ 9.4.6. SubscribeToTask  ](https://a2a-protocol.org/latest/specification/#946-subscribetotask)
          * [ 9.4.7. Push Notification Configuration Methods  ](https://a2a-protocol.org/latest/specification/#947-push-notification-configuration-methods)
          * [ 9.4.8. GetExtendedAgentCard  ](https://a2a-protocol.org/latest/specification/#948-getextendedagentcard)
        * [ 9.5. Error Handling  ](https://a2a-protocol.org/latest/specification/#95-error-handling)
      * [ 10. gRPC Protocol Binding  ](https://a2a-protocol.org/latest/specification/#10-grpc-protocol-binding)
        * [ 10.1. Protocol Requirements  ](https://a2a-protocol.org/latest/specification/#101-protocol-requirements)
        * [ 10.2. Service Parameter Transmission  ](https://a2a-protocol.org/latest/specification/#102-service-parameter-transmission)
        * [ 10.3. Service Definition  ](https://a2a-protocol.org/latest/specification/#103-service-definition)
        * [ 10.4. Core Methods  ](https://a2a-protocol.org/latest/specification/#104-core-methods)
          * [ 10.4.1. SendMessage  ](https://a2a-protocol.org/latest/specification/#1041-sendmessage)
          * [ 10.4.2. SendStreamingMessage  ](https://a2a-protocol.org/latest/specification/#1042-sendstreamingmessage)
          * [ 10.4.3. GetTask  ](https://a2a-protocol.org/latest/specification/#1043-gettask)
          * [ 10.4.4. ListTasks  ](https://a2a-protocol.org/latest/specification/#1044-listtasks)
          * [ 10.4.5. CancelTask  ](https://a2a-protocol.org/latest/specification/#1045-canceltask)
          * [ 10.4.6. SubscribeToTask  ](https://a2a-protocol.org/latest/specification/#1046-subscribetotask)
          * [ 10.4.7. CreateTaskPushNotificationConfig  ](https://a2a-protocol.org/latest/specification/#1047-createtaskpushnotificationconfig)
          * [ 10.4.8. GetTaskPushNotificationConfig  ](https://a2a-protocol.org/latest/specification/#1048-gettaskpushnotificationconfig)
          * [ 10.4.9. ListTaskPushNotificationConfigs  ](https://a2a-protocol.org/latest/specification/#1049-listtaskpushnotificationconfigs)
          * [ 10.4.10. DeleteTaskPushNotificationConfig  ](https://a2a-protocol.org/latest/specification/#10410-deletetaskpushnotificationconfig)
          * [ 10.4.11. GetExtendedAgentCard  ](https://a2a-protocol.org/latest/specification/#10411-getextendedagentcard)
        * [ 10.5. gRPC-Specific Data Types  ](https://a2a-protocol.org/latest/specification/#105-grpc-specific-data-types)
          * [ 10.5.1. TaskPushNotificationConfig  ](https://a2a-protocol.org/latest/specification/#1051-taskpushnotificationconfig)
        * [ 10.6. Error Handling  ](https://a2a-protocol.org/latest/specification/#106-error-handling)
        * [ 10.7. Streaming  ](https://a2a-protocol.org/latest/specification/#107-streaming)
      * [ 11. HTTP+JSON/REST Protocol Binding  ](https://a2a-protocol.org/latest/specification/#11-httpjsonrest-protocol-binding)
        * [ 11.1. Protocol Requirements  ](https://a2a-protocol.org/latest/specification/#111-protocol-requirements)
        * [ 11.2. Service Parameter Transmission  ](https://a2a-protocol.org/latest/specification/#112-service-parameter-transmission)
        * [ 11.3. URL Patterns and HTTP Methods  ](https://a2a-protocol.org/latest/specification/#113-url-patterns-and-http-methods)
          * [ 11.3.1. Message Operations  ](https://a2a-protocol.org/latest/specification/#1131-message-operations)
          * [ 11.3.2. Task Operations  ](https://a2a-protocol.org/latest/specification/#1132-task-operations)
          * [ 11.3.3. Push Notification Configuration  ](https://a2a-protocol.org/latest/specification/#1133-push-notification-configuration)
          * [ 11.3.4. Agent Card  ](https://a2a-protocol.org/latest/specification/#1134-agent-card)
        * [ 11.4. Request/Response Format  ](https://a2a-protocol.org/latest/specification/#114-requestresponse-format)
        * [ 11.5. Query Parameter Naming for Request Parameters  ](https://a2a-protocol.org/latest/specification/#115-query-parameter-naming-for-request-parameters)
        * [ 11.6. Error Handling  ](https://a2a-protocol.org/latest/specification/#116-error-handling)
        * [ 11.7. Streaming  ](https://a2a-protocol.org/latest/specification/#117-streaming)
      * [ 12. Custom Binding Guidelines  ](https://a2a-protocol.org/latest/specification/#12-custom-binding-guidelines)
        * [ 12.1. Binding Requirements  ](https://a2a-protocol.org/latest/specification/#121-binding-requirements)
        * [ 12.2. Data Type Mappings  ](https://a2a-protocol.org/latest/specification/#122-data-type-mappings)
        * [ 12.3. Service Parameter Transmission  ](https://a2a-protocol.org/latest/specification/#123-service-parameter-transmission)
        * [ 12.4. Error Mapping  ](https://a2a-protocol.org/latest/specification/#124-error-mapping)
        * [ 12.5. Streaming Support  ](https://a2a-protocol.org/latest/specification/#125-streaming-support)
        * [ 12.6. Authentication and Authorization  ](https://a2a-protocol.org/latest/specification/#126-authentication-and-authorization)
        * [ 12.7. Agent Card Declaration  ](https://a2a-protocol.org/latest/specification/#127-agent-card-declaration)
        * [ 12.8. Interoperability Testing  ](https://a2a-protocol.org/latest/specification/#128-interoperability-testing)
      * [ 13. Security Considerations  ](https://a2a-protocol.org/latest/specification/#13-security-considerations)
        * [ 13.1. Data Access and Authorization Scoping  ](https://a2a-protocol.org/latest/specification/#131-data-access-and-authorization-scoping)
        * [ 13.2. Push Notification Security  ](https://a2a-protocol.org/latest/specification/#132-push-notification-security)
        * [ 13.3. Extended Agent Card Access Control  ](https://a2a-protocol.org/latest/specification/#133-extended-agent-card-access-control)
        * [ 13.4. General Security Best Practices  ](https://a2a-protocol.org/latest/specification/#134-general-security-best-practices)
      * [ 14. IANA Considerations  ](https://a2a-protocol.org/latest/specification/#14-iana-considerations)
        * [ 14.1. Media Type Registration  ](https://a2a-protocol.org/latest/specification/#141-media-type-registration)
          * [ 14.1.1. application/a2a+json  ](https://a2a-protocol.org/latest/specification/#1411-applicationa2ajson)
        * [ 14.2. HTTP Header Field Registrations  ](https://a2a-protocol.org/latest/specification/#142-http-header-field-registrations)
          * [ 14.2.1. A2A-Version Header  ](https://a2a-protocol.org/latest/specification/#1421-a2a-version-header)
          * [ 14.2.2. A2A-Extensions Header  ](https://a2a-protocol.org/latest/specification/#1422-a2a-extensions-header)
        * [ 14.3. Well-Known URI Registration  ](https://a2a-protocol.org/latest/specification/#143-well-known-uri-registration)
      * [ Appendix A. Migration & Legacy Compatibility  ](https://a2a-protocol.org/latest/specification/#appendix-a-migration-legacy-compatibility)
        * [ A.1 Legacy Documentation Anchors  ](https://a2a-protocol.org/latest/specification/#a1-legacy-documentation-anchors)
        * [ A.2 Migration Guidance  ](https://a2a-protocol.org/latest/specification/#a2-migration-guidance)
          * [ A.2.1 Breaking Change: Kind Discriminator Removed  ](https://a2a-protocol.org/latest/specification/#a21-breaking-change-kind-discriminator-removed)
          * [ A.2.2 Breaking Change: Extended Agent Card Field Relocated  ](https://a2a-protocol.org/latest/specification/#a22-breaking-change-extended-agent-card-field-relocated)
        * [ A.3 Future Automation  ](https://a2a-protocol.org/latest/specification/#a3-future-automation)
      * [ Appendix B. Relationship to MCP (Model Context Protocol)  ](https://a2a-protocol.org/latest/specification/#appendix-b-relationship-to-mcp-model-context-protocol)
    * [ What's New in v1.0  ](https://a2a-protocol.org/latest/whats-new-v1/)
    * [ Protocol Definition  ](https://a2a-protocol.org/latest/definitions/)
  * [ SDK Reference  ](https://a2a-protocol.org/latest/sdk/)
    * [ Python  ](https://a2a-protocol.org/latest/sdk/python/api/)
  * [ Community  ](https://a2a-protocol.org/latest/community/)
  * [ Partners  ](https://a2a-protocol.org/latest/partners/)
  * [ Roadmap  ](https://a2a-protocol.org/latest/roadmap/)


  * [ 1. Introduction  ](https://a2a-protocol.org/latest/specification/#1-introduction)
    * [ 1.1. Key Goals of A2A  ](https://a2a-protocol.org/latest/specification/#11-key-goals-of-a2a)
    * [ 1.2. Guiding Principles  ](https://a2a-protocol.org/latest/specification/#12-guiding-principles)
    * [ 1.3. Specification Structure  ](https://a2a-protocol.org/latest/specification/#13-specification-structure)
    * [ 1.4 Normative Content  ](https://a2a-protocol.org/latest/specification/#14-normative-content)
  * [ 2. Terminology  ](https://a2a-protocol.org/latest/specification/#2-terminology)
    * [ 2.1. Requirements Language  ](https://a2a-protocol.org/latest/specification/#21-requirements-language)
    * [ 2.2. Core Concepts  ](https://a2a-protocol.org/latest/specification/#22-core-concepts)
  * [ 3. A2A Protocol Operations  ](https://a2a-protocol.org/latest/specification/#3-a2a-protocol-operations)
    * [ 3.1. Core Operations  ](https://a2a-protocol.org/latest/specification/#31-core-operations)
      * [ 3.1.1. Send Message  ](https://a2a-protocol.org/latest/specification/#311-send-message)
      * [ 3.1.2. Send Streaming Message  ](https://a2a-protocol.org/latest/specification/#312-send-streaming-message)
      * [ 3.1.3. Get Task  ](https://a2a-protocol.org/latest/specification/#313-get-task)
      * [ 3.1.4. List Tasks  ](https://a2a-protocol.org/latest/specification/#314-list-tasks)
      * [ 3.1.5. Cancel Task  ](https://a2a-protocol.org/latest/specification/#315-cancel-task)
      * [ 3.1.6. Subscribe to Task  ](https://a2a-protocol.org/latest/specification/#316-subscribe-to-task)
      * [ 3.1.7. Create Push Notification Config  ](https://a2a-protocol.org/latest/specification/#317-create-push-notification-config)
      * [ 3.1.8. Get Push Notification Config  ](https://a2a-protocol.org/latest/specification/#318-get-push-notification-config)
      * [ 3.1.9. List Push Notification Configs  ](https://a2a-protocol.org/latest/specification/#319-list-push-notification-configs)
      * [ 3.1.10. Delete Push Notification Config  ](https://a2a-protocol.org/latest/specification/#3110-delete-push-notification-config)
      * [ 3.1.11. Get Extended Agent Card  ](https://a2a-protocol.org/latest/specification/#3111-get-extended-agent-card)
    * [ 3.2. Operation Parameter Objects  ](https://a2a-protocol.org/latest/specification/#32-operation-parameter-objects)
      * [ 3.2.1. SendMessageRequest  ](https://a2a-protocol.org/latest/specification/#321-sendmessagerequest)
      * [ 3.2.2. SendMessageConfiguration  ](https://a2a-protocol.org/latest/specification/#322-sendmessageconfiguration)
      * [ 3.2.3. Stream Response  ](https://a2a-protocol.org/latest/specification/#323-stream-response)
      * [ 3.2.4. History Length Semantics  ](https://a2a-protocol.org/latest/specification/#324-history-length-semantics)
      * [ 3.2.5. Metadata  ](https://a2a-protocol.org/latest/specification/#325-metadata)
      * [ 3.2.6 Service Parameters  ](https://a2a-protocol.org/latest/specification/#326-service-parameters)
    * [ 3.3. Operation Semantics  ](https://a2a-protocol.org/latest/specification/#33-operation-semantics)
      * [ 3.3.1. Idempotency  ](https://a2a-protocol.org/latest/specification/#331-idempotency)
      * [ 3.3.2. Error Handling  ](https://a2a-protocol.org/latest/specification/#332-error-handling)
      * [ 3.3.3. Asynchronous Processing  ](https://a2a-protocol.org/latest/specification/#333-asynchronous-processing)
      * [ 3.3.4. Capability Validation  ](https://a2a-protocol.org/latest/specification/#334-capability-validation)
    * [ 3.4. Multi-Turn Interactions  ](https://a2a-protocol.org/latest/specification/#34-multi-turn-interactions)
      * [ 3.4.1. Context Identifier Semantics  ](https://a2a-protocol.org/latest/specification/#341-context-identifier-semantics)
      * [ 3.4.2. Task Identifier Semantics  ](https://a2a-protocol.org/latest/specification/#342-task-identifier-semantics)
      * [ 3.4.3. Multi-Turn Conversation Patterns  ](https://a2a-protocol.org/latest/specification/#343-multi-turn-conversation-patterns)
    * [ 3.5. Task Update Delivery Mechanisms  ](https://a2a-protocol.org/latest/specification/#35-task-update-delivery-mechanisms)
      * [ 3.5.1. Overview of Update Mechanisms  ](https://a2a-protocol.org/latest/specification/#351-overview-of-update-mechanisms)
      * [ 3.5.2. Streaming Event Delivery  ](https://a2a-protocol.org/latest/specification/#352-streaming-event-delivery)
      * [ 3.5.3. Push Notification Delivery  ](https://a2a-protocol.org/latest/specification/#353-push-notification-delivery)
    * [ 3.6 Versioning  ](https://a2a-protocol.org/latest/specification/#36-versioning)
      * [ 3.6.1 Client Responsibilities  ](https://a2a-protocol.org/latest/specification/#361-client-responsibilities)
      * [ 3.6.2 Server Responsibilities  ](https://a2a-protocol.org/latest/specification/#362-server-responsibilities)
      * [ 3.6.3 Tooling support  ](https://a2a-protocol.org/latest/specification/#363-tooling-support)
    * [ 3.7 Messages and Artifacts  ](https://a2a-protocol.org/latest/specification/#37-messages-and-artifacts)
  * [ 4. Protocol Data Model  ](https://a2a-protocol.org/latest/specification/#4-protocol-data-model)
    * [ 4.1. Core Objects  ](https://a2a-protocol.org/latest/specification/#41-core-objects)
      * [ 4.1.1. Task  ](https://a2a-protocol.org/latest/specification/#411-task)
      * [ 4.1.2. TaskStatus  ](https://a2a-protocol.org/latest/specification/#412-taskstatus)
      * [ 4.1.3. TaskState  ](https://a2a-protocol.org/latest/specification/#413-taskstate)
      * [ 4.1.4. Message  ](https://a2a-protocol.org/latest/specification/#414-message)
      * [ 4.1.5. Role  ](https://a2a-protocol.org/latest/specification/#415-role)
      * [ 4.1.6. Part  ](https://a2a-protocol.org/latest/specification/#416-part)
      * [ 4.1.7. Artifact  ](https://a2a-protocol.org/latest/specification/#417-artifact)
    * [ 4.2. Streaming Events  ](https://a2a-protocol.org/latest/specification/#42-streaming-events)
      * [ 4.2.1. TaskStatusUpdateEvent  ](https://a2a-protocol.org/latest/specification/#421-taskstatusupdateevent)
      * [ 4.2.2. TaskArtifactUpdateEvent  ](https://a2a-protocol.org/latest/specification/#422-taskartifactupdateevent)
    * [ 4.3. Push Notification Objects  ](https://a2a-protocol.org/latest/specification/#43-push-notification-objects)
      * [ 4.3.1. PushNotificationConfig  ](https://a2a-protocol.org/latest/specification/#431-pushnotificationconfig)
      * [ 4.3.2. AuthenticationInfo  ](https://a2a-protocol.org/latest/specification/#432-authenticationinfo)
      * [ 4.3.3. Push Notification Payload  ](https://a2a-protocol.org/latest/specification/#433-push-notification-payload)
    * [ 4.4. Agent Discovery Objects  ](https://a2a-protocol.org/latest/specification/#44-agent-discovery-objects)
      * [ 4.4.1. AgentCard  ](https://a2a-protocol.org/latest/specification/#441-agentcard)
      * [ 4.4.2. AgentProvider  ](https://a2a-protocol.org/latest/specification/#442-agentprovider)
      * [ 4.4.3. AgentCapabilities  ](https://a2a-protocol.org/latest/specification/#443-agentcapabilities)
      * [ 4.4.4. AgentExtension  ](https://a2a-protocol.org/latest/specification/#444-agentextension)
      * [ 4.4.5. AgentSkill  ](https://a2a-protocol.org/latest/specification/#445-agentskill)
      * [ 4.4.6. AgentInterface  ](https://a2a-protocol.org/latest/specification/#446-agentinterface)
      * [ 4.4.7. AgentCardSignature  ](https://a2a-protocol.org/latest/specification/#447-agentcardsignature)
    * [ 4.5. Security Objects  ](https://a2a-protocol.org/latest/specification/#45-security-objects)
      * [ 4.5.1. SecurityScheme  ](https://a2a-protocol.org/latest/specification/#451-securityscheme)
      * [ 4.5.2. APIKeySecurityScheme  ](https://a2a-protocol.org/latest/specification/#452-apikeysecurityscheme)
      * [ 4.5.3. HTTPAuthSecurityScheme  ](https://a2a-protocol.org/latest/specification/#453-httpauthsecurityscheme)
      * [ 4.5.4. OAuth2SecurityScheme  ](https://a2a-protocol.org/latest/specification/#454-oauth2securityscheme)
      * [ 4.5.5. OpenIdConnectSecurityScheme  ](https://a2a-protocol.org/latest/specification/#455-openidconnectsecurityscheme)
      * [ 4.5.6. MutualTlsSecurityScheme  ](https://a2a-protocol.org/latest/specification/#456-mutualtlssecurityscheme)
      * [ 4.5.7. OAuthFlows  ](https://a2a-protocol.org/latest/specification/#457-oauthflows)
      * [ 4.5.8. AuthorizationCodeOAuthFlow  ](https://a2a-protocol.org/latest/specification/#458-authorizationcodeoauthflow)
      * [ 4.5.9. ClientCredentialsOAuthFlow  ](https://a2a-protocol.org/latest/specification/#459-clientcredentialsoauthflow)
      * [ 4.5.10. DeviceCodeOAuthFlow  ](https://a2a-protocol.org/latest/specification/#4510-devicecodeoauthflow)
    * [ 4.6. Extensions  ](https://a2a-protocol.org/latest/specification/#46-extensions)
      * [ 4.6.1. Extension Declaration  ](https://a2a-protocol.org/latest/specification/#461-extension-declaration)
      * [ 4.6.2. Extensions Points  ](https://a2a-protocol.org/latest/specification/#462-extensions-points)
      * [ 4.6.3. Extension Versioning and Compatibility  ](https://a2a-protocol.org/latest/specification/#463-extension-versioning-and-compatibility)
  * [ 5. Protocol Binding Requirements and Interoperability  ](https://a2a-protocol.org/latest/specification/#5-protocol-binding-requirements-and-interoperability)
    * [ 5.1. Functional Equivalence Requirements  ](https://a2a-protocol.org/latest/specification/#51-functional-equivalence-requirements)
    * [ 5.2. Protocol Selection and Negotiation  ](https://a2a-protocol.org/latest/specification/#52-protocol-selection-and-negotiation)
    * [ 5.3. Method Mapping Reference  ](https://a2a-protocol.org/latest/specification/#53-method-mapping-reference)
    * [ 5.4. Error Code Mappings  ](https://a2a-protocol.org/latest/specification/#54-error-code-mappings)
    * [ 5.5. JSON Field Naming Convention  ](https://a2a-protocol.org/latest/specification/#55-json-field-naming-convention)
    * [ 5.6. Data Type Conventions  ](https://a2a-protocol.org/latest/specification/#56-data-type-conventions)
      * [ 5.6.1. Timestamps  ](https://a2a-protocol.org/latest/specification/#561-timestamps)
    * [ 5.7. Field Presence and Optionality  ](https://a2a-protocol.org/latest/specification/#57-field-presence-and-optionality)
  * [ 6. Common Workflows & Examples  ](https://a2a-protocol.org/latest/specification/#6-common-workflows-examples)
    * [ 6.1. Basic Task Execution  ](https://a2a-protocol.org/latest/specification/#61-basic-task-execution)
    * [ 6.2. Streaming Task Execution  ](https://a2a-protocol.org/latest/specification/#62-streaming-task-execution)
    * [ 6.3. Multi-Turn Interaction  ](https://a2a-protocol.org/latest/specification/#63-multi-turn-interaction)
    * [ 6.4. Version Negotiation Error  ](https://a2a-protocol.org/latest/specification/#64-version-negotiation-error)
    * [ 6.5. Task Listing and Management  ](https://a2a-protocol.org/latest/specification/#65-task-listing-and-management)
      * [ Request: All tasks from a specific context  ](https://a2a-protocol.org/latest/specification/#request-all-tasks-from-a-specific-context)
      * [ Request: All working tasks across all contexts  ](https://a2a-protocol.org/latest/specification/#request-all-working-tasks-across-all-contexts)
      * [ Pagination Example  ](https://a2a-protocol.org/latest/specification/#pagination-example)
      * [ Validation Error Example  ](https://a2a-protocol.org/latest/specification/#validation-error-example)
    * [ 6.6. Push Notification Setup and Usage  ](https://a2a-protocol.org/latest/specification/#66-push-notification-setup-and-usage)
    * [ 6.7. File Exchange (Upload and Download)  ](https://a2a-protocol.org/latest/specification/#67-file-exchange-upload-and-download)
    * [ 6.8. Structured Data Exchange  ](https://a2a-protocol.org/latest/specification/#68-structured-data-exchange)
    * [ 6.9. Fetching Authenticated Extended Agent Card  ](https://a2a-protocol.org/latest/specification/#69-fetching-authenticated-extended-agent-card)
    * [ Step 2: Client obtains credentials (out-of-band OAuth 2.0 flow)  ](https://a2a-protocol.org/latest/specification/#step-2-client-obtains-credentials-out-of-band-oauth-20-flow)
    * [ Step 3: Client fetches authenticated extended Agent Card  ](https://a2a-protocol.org/latest/specification/#step-3-client-fetches-authenticated-extended-agent-card)
  * [ 7. Authentication and Authorization  ](https://a2a-protocol.org/latest/specification/#7-authentication-and-authorization)
    * [ 7.1. Protocol Security  ](https://a2a-protocol.org/latest/specification/#71-protocol-security)
    * [ 7.2. Server Identity Verification  ](https://a2a-protocol.org/latest/specification/#72-server-identity-verification)
    * [ 7.3. Client Authentication Process  ](https://a2a-protocol.org/latest/specification/#73-client-authentication-process)
    * [ 7.4. Server Authentication Responsibilities  ](https://a2a-protocol.org/latest/specification/#74-server-authentication-responsibilities)
    * [ 7.5. Server Authorization Responsibilities  ](https://a2a-protocol.org/latest/specification/#75-server-authorization-responsibilities)
    * [ 7.6. In-Task Authorization  ](https://a2a-protocol.org/latest/specification/#76-in-task-authorization)
      * [ 7.6.1 In-Task Authorization Agent Responsibilities  ](https://a2a-protocol.org/latest/specification/#761-in-task-authorization-agent-responsibilities)
      * [ 7.6.2 In-Task Authorization Client Responsibilities  ](https://a2a-protocol.org/latest/specification/#762-in-task-authorization-client-responsibilities)
      * [ 7.6.3 In-Task Authorization Security Considerations  ](https://a2a-protocol.org/latest/specification/#763-in-task-authorization-security-considerations)
  * [ 8. Agent Discovery: The Agent Card  ](https://a2a-protocol.org/latest/specification/#8-agent-discovery-the-agent-card)
    * [ 8.1. Purpose  ](https://a2a-protocol.org/latest/specification/#81-purpose)
    * [ 8.2. Discovery Mechanisms  ](https://a2a-protocol.org/latest/specification/#82-discovery-mechanisms)
    * [ 8.3. Protocol Declaration Requirements  ](https://a2a-protocol.org/latest/specification/#83-protocol-declaration-requirements)
      * [ 8.3.1. Supported Interfaces Declaration  ](https://a2a-protocol.org/latest/specification/#831-supported-interfaces-declaration)
      * [ 8.3.2. Client Protocol Selection  ](https://a2a-protocol.org/latest/specification/#832-client-protocol-selection)
    * [ 8.4. Agent Card Signing  ](https://a2a-protocol.org/latest/specification/#84-agent-card-signing)
      * [ 8.4.1. Canonicalization Requirements  ](https://a2a-protocol.org/latest/specification/#841-canonicalization-requirements)
      * [ 8.4.2. Signature Format  ](https://a2a-protocol.org/latest/specification/#842-signature-format)
      * [ 8.4.3. Signature Verification  ](https://a2a-protocol.org/latest/specification/#843-signature-verification)
    * [ 8.5. Sample Agent Card  ](https://a2a-protocol.org/latest/specification/#85-sample-agent-card)
    * [ 8.6. Caching  ](https://a2a-protocol.org/latest/specification/#86-caching)
      * [ 8.6.1. Server Requirements  ](https://a2a-protocol.org/latest/specification/#861-server-requirements)
      * [ 8.6.2. Client Requirements  ](https://a2a-protocol.org/latest/specification/#862-client-requirements)
  * [ 9. JSON-RPC Protocol Binding  ](https://a2a-protocol.org/latest/specification/#9-json-rpc-protocol-binding)
    * [ 9.1. Protocol Requirements  ](https://a2a-protocol.org/latest/specification/#91-protocol-requirements)
    * [ 9.2. Service Parameter Transmission  ](https://a2a-protocol.org/latest/specification/#92-service-parameter-transmission)
    * [ 9.3. Base Request Structure  ](https://a2a-protocol.org/latest/specification/#93-base-request-structure)
    * [ 9.4. Core Methods  ](https://a2a-protocol.org/latest/specification/#94-core-methods)
      * [ 9.4.1. SendMessage  ](https://a2a-protocol.org/latest/specification/#941-sendmessage)
      * [ 9.4.2. SendStreamingMessage  ](https://a2a-protocol.org/latest/specification/#942-sendstreamingmessage)
      * [ 9.4.3. GetTask  ](https://a2a-protocol.org/latest/specification/#943-gettask)
      * [ 9.4.4. ListTasks  ](https://a2a-protocol.org/latest/specification/#944-listtasks)
      * [ 9.4.5. CancelTask  ](https://a2a-protocol.org/latest/specification/#945-canceltask)
      * [ 9.4.6. SubscribeToTask  ](https://a2a-protocol.org/latest/specification/#946-subscribetotask)
      * [ 9.4.7. Push Notification Configuration Methods  ](https://a2a-protocol.org/latest/specification/#947-push-notification-configuration-methods)
      * [ 9.4.8. GetExtendedAgentCard  ](https://a2a-protocol.org/latest/specification/#948-getextendedagentcard)
    * [ 9.5. Error Handling  ](https://a2a-protocol.org/latest/specification/#95-error-handling)
  * [ 10. gRPC Protocol Binding  ](https://a2a-protocol.org/latest/specification/#10-grpc-protocol-binding)
    * [ 10.1. Protocol Requirements  ](https://a2a-protocol.org/latest/specification/#101-protocol-requirements)
    * [ 10.2. Service Parameter Transmission  ](https://a2a-protocol.org/latest/specification/#102-service-parameter-transmission)
    * [ 10.3. Service Definition  ](https://a2a-protocol.org/latest/specification/#103-service-definition)
    * [ 10.4. Core Methods  ](https://a2a-protocol.org/latest/specification/#104-core-methods)
      * [ 10.4.1. SendMessage  ](https://a2a-protocol.org/latest/specification/#1041-sendmessage)
      * [ 10.4.2. SendStreamingMessage  ](https://a2a-protocol.org/latest/specification/#1042-sendstreamingmessage)
      * [ 10.4.3. GetTask  ](https://a2a-protocol.org/latest/specification/#1043-gettask)
      * [ 10.4.4. ListTasks  ](https://a2a-protocol.org/latest/specification/#1044-listtasks)
      * [ 10.4.5. CancelTask  ](https://a2a-protocol.org/latest/specification/#1045-canceltask)
      * [ 10.4.6. SubscribeToTask  ](https://a2a-protocol.org/latest/specification/#1046-subscribetotask)
      * [ 10.4.7. CreateTaskPushNotificationConfig  ](https://a2a-protocol.org/latest/specification/#1047-createtaskpushnotificationconfig)
      * [ 10.4.8. GetTaskPushNotificationConfig  ](https://a2a-protocol.org/latest/specification/#1048-gettaskpushnotificationconfig)
      * [ 10.4.9. ListTaskPushNotificationConfigs  ](https://a2a-protocol.org/latest/specification/#1049-listtaskpushnotificationconfigs)
      * [ 10.4.10. DeleteTaskPushNotificationConfig  ](https://a2a-protocol.org/latest/specification/#10410-deletetaskpushnotificationconfig)
      * [ 10.4.11. GetExtendedAgentCard  ](https://a2a-protocol.org/latest/specification/#10411-getextendedagentcard)
    * [ 10.5. gRPC-Specific Data Types  ](https://a2a-protocol.org/latest/specification/#105-grpc-specific-data-types)
      * [ 10.5.1. TaskPushNotificationConfig  ](https://a2a-protocol.org/latest/specification/#1051-taskpushnotificationconfig)
    * [ 10.6. Error Handling  ](https://a2a-protocol.org/latest/specification/#106-error-handling)
    * [ 10.7. Streaming  ](https://a2a-protocol.org/latest/specification/#107-streaming)
  * [ 11. HTTP+JSON/REST Protocol Binding  ](https://a2a-protocol.org/latest/specification/#11-httpjsonrest-protocol-binding)
    * [ 11.1. Protocol Requirements  ](https://a2a-protocol.org/latest/specification/#111-protocol-requirements)
    * [ 11.2. Service Parameter Transmission  ](https://a2a-protocol.org/latest/specification/#112-service-parameter-transmission)
    * [ 11.3. URL Patterns and HTTP Methods  ](https://a2a-protocol.org/latest/specification/#113-url-patterns-and-http-methods)
      * [ 11.3.1. Message Operations  ](https://a2a-protocol.org/latest/specification/#1131-message-operations)
      * [ 11.3.2. Task Operations  ](https://a2a-protocol.org/latest/specification/#1132-task-operations)
      * [ 11.3.3. Push Notification Configuration  ](https://a2a-protocol.org/latest/specification/#1133-push-notification-configuration)
      * [ 11.3.4. Agent Card  ](https://a2a-protocol.org/latest/specification/#1134-agent-card)
    * [ 11.4. Request/Response Format  ](https://a2a-protocol.org/latest/specification/#114-requestresponse-format)
    * [ 11.5. Query Parameter Naming for Request Parameters  ](https://a2a-protocol.org/latest/specification/#115-query-parameter-naming-for-request-parameters)
    * [ 11.6. Error Handling  ](https://a2a-protocol.org/latest/specification/#116-error-handling)
    * [ 11.7. Streaming  ](https://a2a-protocol.org/latest/specification/#117-streaming)
  * [ 12. Custom Binding Guidelines  ](https://a2a-protocol.org/latest/specification/#12-custom-binding-guidelines)
    * [ 12.1. Binding Requirements  ](https://a2a-protocol.org/latest/specification/#121-binding-requirements)
    * [ 12.2. Data Type Mappings  ](https://a2a-protocol.org/latest/specification/#122-data-type-mappings)
    * [ 12.3. Service Parameter Transmission  ](https://a2a-protocol.org/latest/specification/#123-service-parameter-transmission)
    * [ 12.4. Error Mapping  ](https://a2a-protocol.org/latest/specification/#124-error-mapping)
    * [ 12.5. Streaming Support  ](https://a2a-protocol.org/latest/specification/#125-streaming-support)
    * [ 12.6. Authentication and Authorization  ](https://a2a-protocol.org/latest/specification/#126-authentication-and-authorization)
    * [ 12.7. Agent Card Declaration  ](https://a2a-protocol.org/latest/specification/#127-agent-card-declaration)
    * [ 12.8. Interoperability Testing  ](https://a2a-protocol.org/latest/specification/#128-interoperability-testing)
  * [ 13. Security Considerations  ](https://a2a-protocol.org/latest/specification/#13-security-considerations)
    * [ 13.1. Data Access and Authorization Scoping  ](https://a2a-protocol.org/latest/specification/#131-data-access-and-authorization-scoping)
    * [ 13.2. Push Notification Security  ](https://a2a-protocol.org/latest/specification/#132-push-notification-security)
    * [ 13.3. Extended Agent Card Access Control  ](https://a2a-protocol.org/latest/specification/#133-extended-agent-card-access-control)
    * [ 13.4. General Security Best Practices  ](https://a2a-protocol.org/latest/specification/#134-general-security-best-practices)
  * [ 14. IANA Considerations  ](https://a2a-protocol.org/latest/specification/#14-iana-considerations)
    * [ 14.1. Media Type Registration  ](https://a2a-protocol.org/latest/specification/#141-media-type-registration)
      * [ 14.1.1. application/a2a+json  ](https://a2a-protocol.org/latest/specification/#1411-applicationa2ajson)
    * [ 14.2. HTTP Header Field Registrations  ](https://a2a-protocol.org/latest/specification/#142-http-header-field-registrations)
      * [ 14.2.1. A2A-Version Header  ](https://a2a-protocol.org/latest/specification/#1421-a2a-version-header)
      * [ 14.2.2. A2A-Extensions Header  ](https://a2a-protocol.org/latest/specification/#1422-a2a-extensions-header)
    * [ 14.3. Well-Known URI Registration  ](https://a2a-protocol.org/latest/specification/#143-well-known-uri-registration)
  * [ Appendix A. Migration & Legacy Compatibility  ](https://a2a-protocol.org/latest/specification/#appendix-a-migration-legacy-compatibility)
    * [ A.1 Legacy Documentation Anchors  ](https://a2a-protocol.org/latest/specification/#a1-legacy-documentation-anchors)
    * [ A.2 Migration Guidance  ](https://a2a-protocol.org/latest/specification/#a2-migration-guidance)
      * [ A.2.1 Breaking Change: Kind Discriminator Removed  ](https://a2a-protocol.org/latest/specification/#a21-breaking-change-kind-discriminator-removed)
      * [ A.2.2 Breaking Change: Extended Agent Card Field Relocated  ](https://a2a-protocol.org/latest/specification/#a22-breaking-change-extended-agent-card-field-relocated)
    * [ A.3 Future Automation  ](https://a2a-protocol.org/latest/specification/#a3-future-automation)
  * [ Appendix B. Relationship to MCP (Model Context Protocol)  ](https://a2a-protocol.org/latest/specification/#appendix-b-relationship-to-mcp-model-context-protocol)


  1. [ Home  ](https://a2a-protocol.org/latest/)
  2. [ Specification  ](https://a2a-protocol.org/latest/specification/)

[ ](https://github.com/a2aproject/A2A/raw/main/docs/specification.md "View source of this page")
# Agent2Agent (A2A) Protocol Specification[¶](https://a2a-protocol.org/latest/specification/#agent2agent-a2a-protocol-specification "Permanent link")
**Latest Released Version** [`1.0.0`](https://a2a-protocol.org/v1.0.0/specification)
**Previous Versions**
  * [`0.3.0`](https://a2a-protocol.org/v0.3.0/specification)
  * [`0.2.6`](https://a2a-protocol.org/v0.2.6/specification)
  * [`0.1.0`](https://a2a-protocol.org/v0.1.0/specification)


See [Release Notes](https://github.com/a2aproject/A2A/releases) for changes made between versions.
## 1. Introduction[¶](https://a2a-protocol.org/latest/specification/#1-introduction "Permanent link")
The Agent2Agent (A2A) Protocol is an open standard designed to facilitate communication and interoperability between independent, potentially opaque AI agent systems. In an ecosystem where agents might be built using different frameworks, languages, or by different vendors, A2A provides a common language and interaction model.
This document provides the detailed technical specification for the A2A protocol. Its primary goal is to enable agents to:
  * Discover each other's capabilities.
  * Negotiate interaction modalities (text, files, structured data).
  * Manage collaborative tasks.
  * Securely exchange information to achieve user goals **without needing access to each other's internal state, memory, or tools.**


### 1.1. Key Goals of A2A[¶](https://a2a-protocol.org/latest/specification/#11-key-goals-of-a2a "Permanent link")
  * **Interoperability:** Bridge the communication gap between disparate agentic systems.
  * **Collaboration:** Enable agents to delegate tasks, exchange context, and work together on complex user requests.
  * **Discovery:** Allow agents to dynamically find and understand the capabilities of other agents.
  * **Flexibility:** Support various interaction modes including synchronous request/response, streaming for real-time updates, and asynchronous push notifications for long-running tasks.
  * **Security:** Facilitate secure communication patterns suitable for enterprise environments, relying on standard web security practices.
  * **Asynchronicity:** Natively support long-running tasks and interactions that may involve human-in-the-loop scenarios.


### 1.2. Guiding Principles[¶](https://a2a-protocol.org/latest/specification/#12-guiding-principles "Permanent link")
  * **Simple:** Reuse existing, well-understood standards (HTTP, JSON-RPC 2.0, Server-Sent Events).
  * **Enterprise Ready:** Address authentication, authorization, security, privacy, tracing, and monitoring by aligning with established enterprise practices.
  * **Async First:** Designed for (potentially very) long-running tasks and human-in-the-loop interactions.
  * **Modality Agnostic:** Support exchange of diverse content types including text, audio/video (via file references), structured data/forms, and potentially embedded UI components (e.g., iframes referenced in parts).
  * **Opaque Execution:** Agents collaborate based on declared capabilities and exchanged information, without needing to share their internal thoughts, plans, or tool implementations.


For a broader understanding of A2A's purpose and benefits, see [What is A2A?](https://a2a-protocol.org/latest/topics/what-is-a2a/).
### 1.3. Specification Structure[¶](https://a2a-protocol.org/latest/specification/#13-specification-structure "Permanent link")
This specification is organized into three distinct layers that work together to provide a complete protocol definition:
**Layer 1: Canonical Data Model** defines the core data structures and message formats that all A2A implementations must understand. These are protocol agnostic definitions expressed as Protocol Buffer messages.
**Layer 2: Abstract Operations** describes the fundamental capabilities and behaviors that A2A agents must support, independent of how they are exposed over specific protocols.
**Layer 3: Protocol Bindings** provides concrete mappings of the abstract operations and data structures to specific protocol bindings (JSON-RPC, gRPC, HTTP/REST), including method names, endpoint patterns, and protocol-specific behaviors.
This layered approach ensures that:
  * Core semantics remain consistent across all protocol bindings
  * New protocol bindings can be added without changing the fundamental data model
  * Developers can reason about A2A operations independently of binding concerns
  * Interoperability is maintained through shared understanding of the canonical data model


### 1.4 Normative Content[¶](https://a2a-protocol.org/latest/specification/#14-normative-content "Permanent link")
In addition to the protocol requirements defined in this document, the file `spec/a2a.proto` is the single authoritative normative definition of all protocol data objects and request/response messages. A generated JSON artifact (`spec/a2a.json`, produced at build time and not committed) MAY be published for convenience to tooling and the website, but it is a non-normative build artifact. SDK language bindings, schemas, and any other derived forms **MUST** be regenerated from the proto (directly or via code generation) rather than edited manually.
**Change Control and Deprecation Lifecycle:**
  * Introduction: When a proto message or field is renamed, the new name is added while existing published names remain available, but marked deprecated, until the next major release.
  * Documentation: Migration guidance MUST be provided via an ancillary document when introducing major breaking changes.
  * Anchors: Legacy documentation anchors MUST be preserved (as hidden HTML anchors) to avoid breaking inbound links.
  * SDK/Schema Aliases: SDKs and JSON Schemas SHOULD provide deprecated alias types/definitions to maintain backward compatibility.
  * Removal: A deprecated name SHOULD NOT be removed earlier than the next major version after introduction of its replacement.


**Automated Generation:**
The documentation build generates `specification/json/a2a.json` on-the-fly (the file is not tracked in source control). Future improvements may publish an OpenAPI v3 + JSON Schema bundle for enhanced tooling.
**Rationale:**
Centering the proto file as the normative source ensures protocol neutrality, reduces specification drift, and provides a deterministic evolution path for the ecosystem.
## 2. Terminology[¶](https://a2a-protocol.org/latest/specification/#2-terminology "Permanent link")
### 2.1. Requirements Language[¶](https://a2a-protocol.org/latest/specification/#21-requirements-language "Permanent link")
The keywords "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://tools.ietf.org/html/rfc2119).
### 2.2. Core Concepts[¶](https://a2a-protocol.org/latest/specification/#22-core-concepts "Permanent link")
A2A revolves around several key concepts. For detailed explanations, please refer to the [Key Concepts guide](https://a2a-protocol.org/latest/topics/key-concepts/).
  * **A2A Client:** An application or agent that initiates requests to an A2A Server on behalf of a user or another system.
  * **A2A Server (Remote Agent):** An agent or agentic system that exposes an A2A-compliant endpoint, processing tasks and providing responses.
  * **Agent Card:** A JSON metadata document published by an A2A Server, describing its identity, capabilities, skills, service endpoint, and authentication requirements.
  * **Message:** A communication turn between a client and a remote agent, having a `role` ("user" or "agent") and containing one or more `Parts`.
  * **Task:** The fundamental unit of work managed by A2A, identified by a unique ID. Tasks are stateful and progress through a defined lifecycle.
  * **Part:** The smallest unit of content within a Message or Artifact. Parts can contain text, file references, or structured data.
  * **Artifact:** An output (e.g., a document, image, structured data) generated by the agent as a result of a task, composed of `Parts`.
  * **Streaming:** Real-time, incremental updates for tasks (status changes, artifact chunks) delivered via protocol-specific streaming mechanisms.
  * **Push Notifications:** Asynchronous task updates delivered via server-initiated HTTP POST requests to a client-provided webhook URL, for long-running or disconnected scenarios.
  * **Context:** An optional identifier to logically group related tasks and messages.
  * **Extension:** A mechanism for agents to provide additional functionality or data beyond the core A2A specification.


## 3. A2A Protocol Operations[¶](https://a2a-protocol.org/latest/specification/#3-a2a-protocol-operations "Permanent link")
This section describes the core operations of the A2A protocol in a binding-independent manner. These operations define the fundamental capabilities that all A2A implementations must support, regardless of the underlying binding mechanism.
### 3.1. Core Operations[¶](https://a2a-protocol.org/latest/specification/#31-core-operations "Permanent link")
The following operations define the fundamental capabilities that all A2A implementations must support, independent of the specific protocol binding used. For a quick reference mapping of these operations to protocol-specific method names and endpoints, see [Section 5.3 (Method Mapping Reference)](https://a2a-protocol.org/latest/specification/#53-method-mapping-reference). For detailed protocol-specific implementation details, see:
  * [Section 9: JSON-RPC Protocol Binding](https://a2a-protocol.org/latest/specification/#9-json-rpc-protocol-binding)
  * [Section 10: gRPC Protocol Binding](https://a2a-protocol.org/latest/specification/#10-grpc-protocol-binding)
  * [Section 11: HTTP+JSON/REST Protocol Binding](https://a2a-protocol.org/latest/specification/#11-httpjsonrest-protocol-binding)


#### 3.1.1. Send Message[¶](https://a2a-protocol.org/latest/specification/#311-send-message "Permanent link")
The primary operation for initiating agent interactions. Clients send a message to an agent and receive either a task that tracks the processing or a direct response message.
**Inputs:**
  * [`SendMessageRequest`](https://a2a-protocol.org/latest/specification/#321-sendmessagerequest): Request object containing the message, configuration, and metadata


**Outputs:**
  * [`Task`](https://a2a-protocol.org/latest/specification/#411-task): A task object representing the processing of the message, OR
  * [`Message`](https://a2a-protocol.org/latest/specification/#414-message): A direct response message (for simple interactions that don't require task tracking)


**Errors:**
  * [`ContentTypeNotSupportedError`](https://a2a-protocol.org/latest/specification/#332-error-handling): A Media Type provided in the request's message parts is not supported by the agent.
  * [`UnsupportedOperationError`](https://a2a-protocol.org/latest/specification/#332-error-handling): Messages sent to Tasks that are in a terminal state (e.g., completed, canceled, rejected) cannot accept further messages.
  * [`TaskNotFoundError`](https://a2a-protocol.org/latest/specification/#332-error-handling): The task ID does not exist or is not accessible.


**Behavior:**
The agent MAY create a new `Task` to process the provided message asynchronously or MAY return a direct `Message` response for simple interactions. The operation MUST return immediately with either task information or response message. Task processing MAY continue asynchronously after the response when a [`Task`](https://a2a-protocol.org/latest/specification/#411-task) is returned.
#### 3.1.2. Send Streaming Message[¶](https://a2a-protocol.org/latest/specification/#312-send-streaming-message "Permanent link")
Similar to Send Message but with real-time streaming of updates during processing.
**Inputs:**
  * [`SendMessageRequest`](https://a2a-protocol.org/latest/specification/#321-sendmessagerequest): Request object containing the message, configuration, and metadata


**Outputs:**
  * [`Stream Response`](https://a2a-protocol.org/latest/specification/#323-stream-response) object containing:
    * Initial response: [`Task`](https://a2a-protocol.org/latest/specification/#411-task) object OR [`Message`](https://a2a-protocol.org/latest/specification/#414-message) object
    * Subsequent events following a `Task` MAY include stream of [`TaskStatusUpdateEvent`](https://a2a-protocol.org/latest/specification/#421-taskstatusupdateevent) and [`TaskArtifactUpdateEvent`](https://a2a-protocol.org/latest/specification/#422-taskartifactupdateevent) objects
  * Final completion indicator


**Errors:**
  * [`UnsupportedOperationError`](https://a2a-protocol.org/latest/specification/#332-error-handling): Streaming is not supported by the agent (see [Capability Validation](https://a2a-protocol.org/latest/specification/#334-capability-validation)).
  * [`UnsupportedOperationError`](https://a2a-protocol.org/latest/specification/#332-error-handling): Messages sent to Tasks that are in a terminal state (e.g., completed, canceled, rejected) cannot accept further messages.
  * [`ContentTypeNotSupportedError`](https://a2a-protocol.org/latest/specification/#332-error-handling): A Media Type provided in the request's message parts is not supported by the agent.
  * [`TaskNotFoundError`](https://a2a-protocol.org/latest/specification/#332-error-handling): The task ID does not exist or is not accessible.


**Behavior:**
The operation MUST establish a streaming connection for real-time updates. The stream MUST follow one of these patterns:
  1. **Message-only stream:** If the agent returns a [`Message`](https://a2a-protocol.org/latest/specification/#414-message), the stream MUST contain exactly one `Message` object and then close immediately. No task tracking or updates are provided.
  2. **Task lifecycle stream:** If the agent returns a [`Task`](https://a2a-protocol.org/latest/specification/#411-task), the stream MUST begin with the Task object, followed by zero or more [`TaskStatusUpdateEvent`](https://a2a-protocol.org/latest/specification/#421-taskstatusupdateevent) or [`TaskArtifactUpdateEvent`](https://a2a-protocol.org/latest/specification/#422-taskartifactupdateevent) objects. The stream MUST close when the task reaches a terminal state (e.g. completed, failed, canceled, rejected).


The agent MAY return a `Task` for complex processing with status/artifact updates or MAY return a `Message` for direct streaming responses without task overhead. The implementation MUST provide immediate feedback on progress and intermediate results.
#### 3.1.3. Get Task[¶](https://a2a-protocol.org/latest/specification/#313-get-task "Permanent link")
Retrieves the current state (including status, artifacts, and optionally history) of a previously initiated task. This is typically used for polling the status of a task initiated with message/send, or for fetching the final state of a task after being notified via a push notification or after a stream has ended.
**Inputs:**
Represents a request for the `GetTask` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Optional. Tenant ID, provided as a path parameter.  |  
| `id`  | `string`  | Yes  | The resource ID of the task to retrieve.  |  
| `historyLength`  | `integer`  | No  | The maximum number of most recent messages from the task's history to retrieve. An unset value means the client does not impose any limit. A value of zero is a request to not include any messages. The server MUST NOT return more messages than the provided value, but MAY apply a lower limit.  |  
See [History Length Semantics](https://a2a-protocol.org/latest/specification/#324-history-length-semantics) for details about `historyLength`.
**Outputs:**
  * [`Task`](https://a2a-protocol.org/latest/specification/#411-task): Current state and artifacts of the requested task


**Errors:**
  * [`TaskNotFoundError`](https://a2a-protocol.org/latest/specification/#332-error-handling): The task ID does not exist or is not accessible.


#### 3.1.4. List Tasks[¶](https://a2a-protocol.org/latest/specification/#314-list-tasks "Permanent link")
Retrieves a list of tasks with optional filtering and pagination capabilities. This method allows clients to discover and manage multiple tasks across different contexts or with specific status criteria.
**Inputs:**
Parameters for listing tasks with optional filtering criteria.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Tenant ID, provided as a path parameter.  |  
| `contextId`  | `string`  | No  | Filter tasks by context ID to get tasks from a specific conversation or session.  |  
| `status`  | [`TaskState`](https://a2a-protocol.org/latest/specification/#taskstate)  | No  | Filter tasks by their current status state.  |  
| `pageSize`  | `integer`  | No  | The maximum number of tasks to return. The service may return fewer than this value. If unspecified, at most 50 tasks will be returned. The minimum value is 1. The maximum value is 100.  |  
| `pageToken`  | `string`  | No  | A page token, received from a previous `ListTasks` call. `ListTasksResponse.next_page_token`. Provide this to retrieve the subsequent page.  |  
| `historyLength`  | `integer`  | No  | The maximum number of messages to include in each task's history.  |  
| `statusTimestampAfter`  | `timestamp`  | No  | Filter tasks which have a status updated after the provided timestamp in ISO 8601 format (e.g., "2023-10-27T10:00:00Z"). Only tasks with a status timestamp time greater than or equal to this value will be returned.  |  
| `includeArtifacts`  | `boolean`  | No  | Whether to include artifacts in the returned tasks. Defaults to false to reduce payload size.  |  
When `includeArtifacts` is false (the default), the artifacts field MUST be omitted entirely from each Task object in the response. The field should not be present as an empty array or null value. When `includeArtifacts` is true, the artifacts field should be included with its actual content (which may be an empty array if the task has no artifacts).
**Outputs:**
Result object for `ListTasks` method containing an array of tasks and pagination information.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tasks`  | array of [`Task`](https://a2a-protocol.org/latest/specification/#task)  | Yes  | Array of tasks matching the specified criteria.  |  
| `nextPageToken`  | `string`  | Yes  | A token to retrieve the next page of results, or empty if there are no more results in the list.  |  
| `pageSize`  | `integer`  | Yes  | The page size used for this response.  |  
| `totalSize`  | `integer`  | Yes  | Total number of tasks available (before pagination).  |  
Note on `nextPageToken`: The `nextPageToken` field MUST always be present in the response. When there are no more results to retrieve (i.e., this is the final page), the field MUST be set to an empty string (""). Clients should check for an empty string to determine if more pages are available.
**Errors:**
None specific to this operation beyond standard protocol errors.
**Behavior:**
The operation MUST return only tasks visible to the authenticated client and MUST use cursor-based pagination for performance and consistency. Tasks MUST be sorted by last update time in descending order. Implementations MUST implement appropriate authorization scoping to ensure clients can only access authorized tasks. See [Section 13.1 Data Access and Authorization Scoping](https://a2a-protocol.org/latest/specification/#131-data-access-and-authorization-scoping) for detailed security requirements.
**_Pagination Strategy:_**
This method uses cursor-based pagination (via `pageToken`/`nextPageToken`) rather than offset-based pagination for better performance and consistency, especially with large datasets. Cursor-based pagination avoids the "deep pagination problem" where skipping large numbers of records becomes inefficient for databases. This approach is consistent with the gRPC specification, which also uses cursor-based pagination (page_token/next_page_token).
**_Ordering:_**
Implementations MUST return tasks sorted by their status timestamp time in descending order (most recently updated tasks first). This ensures consistent pagination and allows clients to efficiently monitor recent task activity.
#### 3.1.5. Cancel Task[¶](https://a2a-protocol.org/latest/specification/#315-cancel-task "Permanent link")
Requests the cancellation of an ongoing task. The server will attempt to cancel the task, but success is not guaranteed (e.g., the task might have already completed or failed, or cancellation might not be supported at its current stage).
**Inputs:**
Represents a request for the `CancelTask` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Optional. Tenant ID, provided as a path parameter.  |  
| `id`  | `string`  | Yes  | The resource ID of the task to cancel.  |  
| `metadata`  | `object`  | No  | A flexible key-value map for passing additional context or parameters.  |  
**Outputs:**
  * Updated [`Task`](https://a2a-protocol.org/latest/specification/#411-task) with cancellation status


**Errors:**
  * [`TaskNotCancelableError`](https://a2a-protocol.org/latest/specification/#332-error-handling): The task is not in a cancelable state (e.g., already completed, failed, or canceled).
  * [`TaskNotFoundError`](https://a2a-protocol.org/latest/specification/#332-error-handling): The task ID does not exist or is not accessible.


**Behavior:**
The operation attempts to cancel the specified task and returns its updated state.
#### 3.1.6. Subscribe to Task[¶](https://a2a-protocol.org/latest/specification/#316-subscribe-to-task "Permanent link")
Establishes a streaming connection to receive updates for an existing task.
**Inputs:**
Represents a request for the `SubscribeToTask` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Optional. Tenant ID, provided as a path parameter.  |  
| `id`  | `string`  | Yes  | The resource ID of the task to subscribe to.  |  
**Outputs:**
  * [`Stream Response`](https://a2a-protocol.org/latest/specification/#323-stream-response) object containing:
    * Initial response: [`Task`](https://a2a-protocol.org/latest/specification/#411-task) object with current state
    * Stream of [`TaskStatusUpdateEvent`](https://a2a-protocol.org/latest/specification/#421-taskstatusupdateevent) and [`TaskArtifactUpdateEvent`](https://a2a-protocol.org/latest/specification/#422-taskartifactupdateevent) objects


**Errors:**
  * [`UnsupportedOperationError`](https://a2a-protocol.org/latest/specification/#332-error-handling): Streaming is not supported by the agent (see [Capability Validation](https://a2a-protocol.org/latest/specification/#334-capability-validation)).
  * [`TaskNotFoundError`](https://a2a-protocol.org/latest/specification/#332-error-handling): The task ID does not exist or is not accessible.
  * [`UnsupportedOperationError`](https://a2a-protocol.org/latest/specification/#332-error-handling): The operation is attempted on a task that is in a terminal state (`completed`, `failed`, `canceled`, or `rejected`).


**Behavior:**
The operation enables real-time monitoring of task progress and can be used with any task that is not in a terminal state. The stream MUST terminate when the task reaches a terminal state (`completed`, `failed`, `canceled`, or `rejected`).
The operation MUST return a `Task` object as the first event in the stream, representing the current state of the task at the time of subscription. This prevents a potential loss of information between a call to `GetTask` and calling `SubscribeToTask`.
#### 3.1.7. Create Push Notification Config[¶](https://a2a-protocol.org/latest/specification/#317-create-push-notification-config "Permanent link")
Creates a push notification configuration for a task to receive asynchronous updates via webhook.
**Inputs:**
**Error:** Message `CreateTaskPushNotificationConfigRequest` not found.
**Outputs:**
  * [`PushNotificationConfig`](https://a2a-protocol.org/latest/specification/#431-pushnotificationconfig): Created configuration with assigned ID


**Errors:**
  * [`PushNotificationNotSupportedError`](https://a2a-protocol.org/latest/specification/#332-error-handling): Push notifications are not supported by the agent (see [Capability Validation](https://a2a-protocol.org/latest/specification/#334-capability-validation)).
  * [`TaskNotFoundError`](https://a2a-protocol.org/latest/specification/#332-error-handling): The task ID does not exist or is not accessible.


**Behavior:**
The operation MUST establish a webhook endpoint for task update notifications. When task updates occur, the agent will send HTTP POST requests to the configured webhook URL with [`StreamResponse`](https://a2a-protocol.org/latest/specification/#323-stream-response) payloads (see [Push Notification Payload](https://a2a-protocol.org/latest/specification/#433-push-notification-payload) for details). This operation is only available if the agent supports push notifications capability. The configuration MUST persist until task completion or explicit deletion.
#### 3.1.8. Get Push Notification Config[¶](https://a2a-protocol.org/latest/specification/#318-get-push-notification-config "Permanent link")
Retrieves an existing push notification configuration for a task.
**Inputs:**
Represents a request for the `GetTaskPushNotificationConfig` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Optional. Tenant ID, provided as a path parameter.  |  
| `taskId`  | `string`  | Yes  | The parent task resource ID.  |  
| `id`  | `string`  | Yes  | The resource ID of the configuration to retrieve.  |  
**Outputs:**
  * [`PushNotificationConfig`](https://a2a-protocol.org/latest/specification/#431-pushnotificationconfig): The requested configuration


**Errors:**
  * [`PushNotificationNotSupportedError`](https://a2a-protocol.org/latest/specification/#332-error-handling): Push notifications are not supported by the agent (see [Capability Validation](https://a2a-protocol.org/latest/specification/#334-capability-validation)).
  * [`TaskNotFoundError`](https://a2a-protocol.org/latest/specification/#332-error-handling): The push notification configuration does not exist.


**Behavior:**
The operation MUST return configuration details including webhook URL and notification settings. The operation MUST fail if the configuration does not exist or the client lacks access.
#### 3.1.9. List Push Notification Configs[¶](https://a2a-protocol.org/latest/specification/#319-list-push-notification-configs "Permanent link")
Retrieves all push notification configurations for a task.
**Inputs:**
Represents a request for the `ListTaskPushNotificationConfigs` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Optional. Tenant ID, provided as a path parameter.  |  
| `taskId`  | `string`  | Yes  | The parent task resource ID.  |  
| `pageSize`  | `integer`  | No  | The maximum number of configurations to return.  |  
| `pageToken`  | `string`  | No  | A page token received from a previous `ListTaskPushNotificationConfigsRequest` call.  |  
**Outputs:**
Represents a successful response for the `ListTaskPushNotificationConfigs` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `configs`  | array of [`TaskPushNotificationConfig`](https://a2a-protocol.org/latest/specification/#taskpushnotificationconfig)  | No  | The list of push notification configurations.  |  
| `nextPageToken`  | `string`  | No  | A token to retrieve the next page of results, or empty if there are no more results in the list.  |  
**Errors:**
  * [`PushNotificationNotSupportedError`](https://a2a-protocol.org/latest/specification/#332-error-handling): Push notifications are not supported by the agent (see [Capability Validation](https://a2a-protocol.org/latest/specification/#334-capability-validation)).
  * [`TaskNotFoundError`](https://a2a-protocol.org/latest/specification/#332-error-handling): The task ID does not exist or is not accessible.


**Behavior:**
The operation MUST return all active push notification configurations for the specified task and MAY support pagination for tasks with many configurations.
#### 3.1.10. Delete Push Notification Config[¶](https://a2a-protocol.org/latest/specification/#3110-delete-push-notification-config "Permanent link")
Removes a push notification configuration for a task.
**Inputs:**
Represents a request for the `DeleteTaskPushNotificationConfig` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Optional. Tenant ID, provided as a path parameter.  |  
| `taskId`  | `string`  | Yes  | The parent task resource ID.  |  
| `id`  | `string`  | Yes  | The resource ID of the configuration to delete.  |  
**Outputs:**
  * Confirmation of deletion (implementation-specific)


**Errors:**
  * [`PushNotificationNotSupportedError`](https://a2a-protocol.org/latest/specification/#332-error-handling): Push notifications are not supported by the agent (see [Capability Validation](https://a2a-protocol.org/latest/specification/#334-capability-validation)).
  * [`TaskNotFoundError`](https://a2a-protocol.org/latest/specification/#332-error-handling): The task ID does not exist.


**Behavior:**
The operation MUST permanently remove the specified push notification configuration. No further notifications will be sent to the configured webhook after deletion. This operation MUST be idempotent - multiple deletions of the same config have the same effect.
#### 3.1.11. Get Extended Agent Card[¶](https://a2a-protocol.org/latest/specification/#3111-get-extended-agent-card "Permanent link")
Retrieves a potentially more detailed version of the Agent Card after the client has authenticated. This endpoint is available only if `AgentCard.capabilities.extendedAgentCard` is `true`.
**Inputs:**
Represents a request for the `GetExtendedAgentCard` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Optional. Tenant ID, provided as a path parameter.  |  
**Outputs:**
  * [`AgentCard`](https://a2a-protocol.org/latest/specification/#441-agentcard): A complete Agent Card object, which may contain additional details or skills not present in the public card


**Errors:**
  * [`UnsupportedOperationError`](https://a2a-protocol.org/latest/specification/#332-error-handling): The agent does not support authenticated extended cards (see [Capability Validation](https://a2a-protocol.org/latest/specification/#334-capability-validation)).
  * [`ExtendedAgentCardNotConfiguredError`](https://a2a-protocol.org/latest/specification/#332-error-handling): The agent declares support but does not have an extended agent card configured.


**Behavior:**
  * **Authentication** : The client MUST authenticate the request using one of the schemes declared in the public `AgentCard.securitySchemes` and `AgentCard.security` fields.
  * **Extended Information** : The operation MAY return different details based on client authentication level, including additional skills, capabilities, or configuration not available in the public Agent Card.
  * **Card Replacement** : Clients retrieving this extended card SHOULD replace their cached public Agent Card with the content received from this endpoint for the duration of their authenticated session or until the card's version changes.
  * **Availability** : This operation is only available if the public Agent Card declares `capabilities.extendedAgentCard: true`.


For detailed security guidance on extended agent cards, see [Section 13.3 Extended Agent Card Access Control](https://a2a-protocol.org/latest/specification/#133-extended-agent-card-access-control).
### 3.2. Operation Parameter Objects[¶](https://a2a-protocol.org/latest/specification/#32-operation-parameter-objects "Permanent link")
This section defines common parameter objects used across multiple operations.
#### 3.2.1. SendMessageRequest[¶](https://a2a-protocol.org/latest/specification/#321-sendmessagerequest "Permanent link")
Represents a request for the `SendMessage` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Optional. Tenant ID, provided as a path parameter.  |  
| `message`  | [`Message`](https://a2a-protocol.org/latest/specification/#message)  | Yes  | The message to send to the agent.  |  
| `configuration`  | [`SendMessageConfiguration`](https://a2a-protocol.org/latest/specification/#sendmessageconfiguration)  | No  | Configuration for the send request.  |  
| `metadata`  | `object`  | No  | A flexible key-value map for passing additional context or parameters.  |  
#### 3.2.2. SendMessageConfiguration[¶](https://a2a-protocol.org/latest/specification/#322-sendmessageconfiguration "Permanent link")
Configuration of a send message request.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `acceptedOutputModes`  | array of `string`  | No  | A list of media types the client is prepared to accept for response parts. Agents SHOULD use this to tailor their output.  |  
| `taskPushNotificationConfig`  | [`TaskPushNotificationConfig`](https://a2a-protocol.org/latest/specification/#taskpushnotificationconfig)  | No  | Configuration for the agent to send push notifications for task updates. Task id should be empty when sending this configuration in a `SendMessage` request.  |  
| `historyLength`  | `integer`  | No  | The maximum number of most recent messages from the task's history to retrieve in the response. An unset value means the client does not impose any limit. A value of zero is a request to not include any messages. The server MUST NOT return more messages than the provided value, but MAY apply a lower limit.  |  
| `returnImmediately`  | `boolean`  | No  | If `true`, the operation returns immediately after creating the task, even if processing is still in progress. If `false` (default), the operation MUST wait until the task reaches a terminal (`COMPLETED`, `FAILED`, `CANCELED`, `REJECTED`) or interrupted (`INPUT_REQUIRED`, `AUTH_REQUIRED`) state before returning.  |  
**Execution Mode:**
The `return_immediately` field in [`SendMessageConfiguration`](https://a2a-protocol.org/latest/specification/#322-sendmessageconfiguration) controls whether the operation returns immediately or waits for task completion. Operations are blocking by default:
  * **Blocking (`return_immediately: false` or unset)**: The operation MUST wait until the task reaches a terminal state (`COMPLETED`, `FAILED`, `CANCELED`, `REJECTED`) or an interrupted state (`INPUT_REQUIRED`, `AUTH_REQUIRED`) before returning. The response MUST include the latest task state with all artifacts and status information. This is the default behavior.
  * **Non-Blocking (`return_immediately: true`)**: The operation MUST return immediately after creating the task, even if processing is still in progress. The returned task will have an in-progress state (e.g., `working`, `input_required`). It is the caller's responsibility to poll for updates using [Get Task](https://a2a-protocol.org/latest/specification/#313-get-task), subscribe via [Subscribe to Task](https://a2a-protocol.org/latest/specification/#316-subscribe-to-task), or receive updates via push notifications.


The `return_immediately` field has no effect:
  * when the operation returns a direct [`Message`](https://a2a-protocol.org/latest/specification/#414-message) response instead of a task.
  * for streaming operations, which always return updates in real-time.
  * on configured push notification configurations, which operates independently of execution mode.


#### 3.2.3. Stream Response[¶](https://a2a-protocol.org/latest/specification/#323-stream-response "Permanent link")
A wrapper object used in streaming operations to encapsulate different types of response data.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `task`  | [`Task`](https://a2a-protocol.org/latest/specification/#task)  | Optional (OneOf)  | A Task object containing the current state of the task.  |  
| `message`  | [`Message`](https://a2a-protocol.org/latest/specification/#message)  | Optional (OneOf)  | A Message object containing a message from the agent.  |  
| `statusUpdate`  | [`TaskStatusUpdateEvent`](https://a2a-protocol.org/latest/specification/#taskstatusupdateevent)  | Optional (OneOf)  | An event indicating a task status update.  |  
| `artifactUpdate`  | [`TaskArtifactUpdateEvent`](https://a2a-protocol.org/latest/specification/#taskartifactupdateevent)  | Optional (OneOf)  | An event indicating a task artifact update.  |  
**Note:** A `StreamResponse` MUST contain exactly one of the following: `task`, `message`, `statusUpdate`, `artifactUpdate`
This wrapper allows streaming endpoints to return different types of updates through a single response stream while maintaining type safety.
#### 3.2.4. History Length Semantics[¶](https://a2a-protocol.org/latest/specification/#324-history-length-semantics "Permanent link")
The `historyLength` parameter appears in multiple operations and controls how much task history is returned in responses. This parameter follows consistent semantics across all operations:
  * **Unset/undefined** : No limit imposed; server returns its default amount of history (implementation-defined, may be all history)
  * **0** : No history should be returned; the `history` field SHOULD be omitted
  * **> 0**: Return at most this many recent messages from the task's history


#### 3.2.5. Metadata[¶](https://a2a-protocol.org/latest/specification/#325-metadata "Permanent link")
A flexible key-value map for passing additional context or parameters with operations. Metadata keys and are strings and values can be any valid value that can be represented in JSON. [`Extensions`](https://a2a-protocol.org/latest/specification/#46-extensions) can be used to strongly type metadata values for specific use cases.
#### 3.2.6 Service Parameters[¶](https://a2a-protocol.org/latest/specification/#326-service-parameters "Permanent link")
A key-value map for passing horizontally applicable context or parameters with case-insensitive string keys and case-sensitive string values. The transmission mechanism for these service parameter key-value pairs is defined by the specific protocol binding (e.g., HTTP headers for HTTP-based bindings, gRPC metadata for gRPC bindings). Custom protocol bindings **MUST** specify how service parameters are transmitted in their binding specification.
**Standard A2A Service Parameters:**  
| Name  | Description  | Example Value  |  
| --- | --- | --- |  
| `A2A-Extensions`  | Comma-separated list of extension URIs that the client wants to use for the request  | `https://example.com/extensions/geolocation/v1,https://standards.org/extensions/citations/v1`  |  
| `A2A-Version`  | The A2A protocol version that the client is using. If the version is not supported, the agent returns [`VersionNotSupportedError`](https://a2a-protocol.org/latest/specification/#332-error-handling)  | `0.3`  |  
As service parameter names MAY need to co-exist with other parameters defined by the underlying transport protocol or infrastructure, all service parameters defined by this specification will be prefixed with `a2a-`.
### 3.3. Operation Semantics[¶](https://a2a-protocol.org/latest/specification/#33-operation-semantics "Permanent link")
#### 3.3.1. Idempotency[¶](https://a2a-protocol.org/latest/specification/#331-idempotency "Permanent link")
  * **Get operations** (Get Task, List Tasks, Get Extended Agent Card) are naturally idempotent
  * **Send Message** operations MAY be idempotent. Agents may utilize the messageId to detect duplicate messages.
  * **Cancel Task** operations are idempotent - multiple cancellation requests have the same effect. A duplicate cancellation request MAY return `TaskNotFoundError` if the task has already been canceled and purged.


#### 3.3.2. Error Handling[¶](https://a2a-protocol.org/latest/specification/#332-error-handling "Permanent link")
All operations may return errors in the following categories. Servers **MUST** return appropriate errors and **SHOULD** provide actionable information to help clients resolve issues.
**Error Categories and Server Requirements:**
  * **Authentication Errors** : Invalid or missing credentials
    * Servers **MUST** reject requests with invalid or missing authentication credentials
    * Servers **SHOULD** include authentication challenge information in the error response
    * Servers **SHOULD** specify which authentication scheme is required
    * Example error codes: HTTP `401 Unauthorized`, gRPC `UNAUTHENTICATED`, JSON-RPC custom error
    * Example scenarios: Missing bearer token, expired API key, invalid OAuth token
  * **Authorization Errors** : Insufficient permissions for requested operation
    * Servers **MUST** return an authorization error when the authenticated client lacks required permissions
    * Servers **SHOULD** indicate what permission or scope is missing (without leaking sensitive information about resources the client cannot access)
    * Servers **MUST NOT** reveal the existence of resources the client is not authorized to access
    * Example error codes: HTTP `403 Forbidden`, gRPC `PERMISSION_DENIED`, JSON-RPC custom error
    * Example scenarios: Attempting to access a task created by another user, insufficient OAuth scopes
  * **Validation Errors** : Invalid input parameters or message format
    * Servers **MUST** validate all input parameters before processing
    * Servers **SHOULD** specify which parameter(s) failed validation and why
    * Servers **SHOULD** provide guidance on valid parameter values or formats
    * Example error codes: HTTP `400 Bad Request`, gRPC `INVALID_ARGUMENT`, JSON-RPC `-32602 Invalid params`
    * Example scenarios: Invalid task ID format, missing required message parts, unsupported content type
  * **Resource Errors** : Requested task not found or not accessible
    * Servers **MUST** return a not found error when a requested resource does not exist or is not accessible to the authenticated client
    * Servers **SHOULD NOT** distinguish between "does not exist" and "not authorized" to prevent information leakage
    * Example error codes: HTTP `404 Not Found`, gRPC `NOT_FOUND`, JSON-RPC custom error (see A2A-specific errors)
    * Example scenarios: Task ID does not exist, task has been deleted, configuration not found
  * **System Errors** : Internal agent failures or temporary unavailability
    * Servers **SHOULD** return appropriate error codes for temporary failures vs. permanent errors
    * Servers **MAY** include retry guidance (e.g., Retry-After header in HTTP)
    * Servers **SHOULD** log system errors for diagnostic purposes
    * Example error codes: HTTP `500 Internal Server Error` or `503 Service Unavailable`, gRPC `INTERNAL` or `UNAVAILABLE`, JSON-RPC `-32603 Internal error`
    * Example scenarios: Database connection failure, downstream service timeout, rate limit exceeded


**Error Payload Structure:**
All error responses in the A2A protocol, regardless of binding, **MUST** convey the following information:
  1. **Error Code** : A machine-readable identifier for the error type (e.g., string code, numeric code, or protocol-specific status)
  2. **Error Message** : A human-readable description of the error
  3. **Error Details** (optional): Additional structured information about the error, such as:
     * Affected fields or parameters
     * Contextual information (e.g., task ID, timestamp)
     * Suggestions for resolution


Protocol bindings **MUST** map these elements to their native error representations while preserving semantic meaning. See binding-specific sections for concrete error format examples: [JSON-RPC Error Handling](https://a2a-protocol.org/latest/specification/#95-error-handling), [gRPC Error Handling](https://a2a-protocol.org/latest/specification/#106-error-handling), and [HTTP/REST Error Handling](https://a2a-protocol.org/latest/specification/#116-error-handling).
**A2A-Specific Errors:**  
| Error Name  | Description  |  
| --- | --- |  
| `TaskNotFoundError`  | The specified task ID does not correspond to an existing or accessible task. It might be invalid, expired, or already completed and purged.  |  
| `TaskNotCancelableError`  | An attempt was made to cancel a task that is not in a cancelable state (e.g., it has already reached a terminal state like `completed`, `failed`, or `canceled`).  |  
| `PushNotificationNotSupportedError`  | Client attempted to use push notification features but the server agent does not support them (i.e., `AgentCard.capabilities.pushNotifications` is `false`).  |  
| `UnsupportedOperationError`  | The requested operation or a specific aspect of it is not supported by this server agent implementation.  |  
| `ContentTypeNotSupportedError`  | A Media Type provided in the request's message parts or implied for an artifact is not supported by the agent or the specific skill being invoked.  |  
| `InvalidAgentResponseError`  | An agent returned a response that does not conform to the specification for the current method.  |  
| `ExtendedAgentCardNotConfiguredError`  | The agent does not have an extended agent card configured when one is required for the requested operation.  |  
| `ExtensionSupportRequiredError`  | Server requested use of an extension marked as `required: true` in the Agent Card but the client did not declare support for it in the request.  |  
| `VersionNotSupportedError`  | The A2A protocol version specified in the request (via `A2A-Version` service parameter) is not supported by the agent.  |  
#### 3.3.3. Asynchronous Processing[¶](https://a2a-protocol.org/latest/specification/#333-asynchronous-processing "Permanent link")
A2A operations are designed for asynchronous task execution. Operations return immediately with either [`Task`](https://a2a-protocol.org/latest/specification/#411-task) objects or [`Message`](https://a2a-protocol.org/latest/specification/#414-message) objects, and when a Task is returned, processing continues in the background. Clients retrieve task updates through polling, streaming, or push notifications (see [Section 3.5](https://a2a-protocol.org/latest/specification/#35-task-update-delivery-mechanisms)). Agents MAY accept additional messages for tasks in non-terminal states to enable multi-turn interactions (see [Section 3.4](https://a2a-protocol.org/latest/specification/#34-multi-turn-interactions)).
#### 3.3.4. Capability Validation[¶](https://a2a-protocol.org/latest/specification/#334-capability-validation "Permanent link")
Agents declare optional capabilities in their [`AgentCard`](https://a2a-protocol.org/latest/specification/#441-agentcard). When clients attempt to use operations or features that require capabilities not declared as supported in the Agent Card, the agent **MUST** return an appropriate error response:
  * **Push Notifications** : If `AgentCard.capabilities.pushNotifications` is `false` or not present, operations related to push notification configuration (Create, Get, List, Delete) **MUST** return [`PushNotificationNotSupportedError`](https://a2a-protocol.org/latest/specification/#332-error-handling).
  * **Streaming** : If `AgentCard.capabilities.streaming` is `false` or not present, attempts to use `SendStreamingMessage` or `SubscribeToTask` operations **MUST** return [`UnsupportedOperationError`](https://a2a-protocol.org/latest/specification/#332-error-handling).
  * **Extended Agent Card** : If `AgentCard.capabilities.extendedAgentCard` is `false` or not present, attempts to call the Get Extended Agent Card operation **MUST** return [`UnsupportedOperationError`](https://a2a-protocol.org/latest/specification/#332-error-handling). If the agent declares support but has not configured an extended card, it **MUST** return [`ExtendedAgentCardNotConfiguredError`](https://a2a-protocol.org/latest/specification/#332-error-handling).
  * **Extensions** : When a server requests use of an extension marked as `required: true` in the Agent Card but the client does not declare support for it, the agent **MUST** return [`ExtensionSupportRequiredError`](https://a2a-protocol.org/latest/specification/#332-error-handling).


Clients **SHOULD** validate capability support by examining the Agent Card before attempting operations that require optional capabilities.
### 3.4. Multi-Turn Interactions[¶](https://a2a-protocol.org/latest/specification/#34-multi-turn-interactions "Permanent link")
The A2A protocol supports multi-turn conversations through context identifiers and task references, enabling agents to maintain conversational continuity across multiple interactions.
#### 3.4.1. Context Identifier Semantics[¶](https://a2a-protocol.org/latest/specification/#341-context-identifier-semantics "Permanent link")
A `contextId` is an identifier that logically groups multiple related [`Task`](https://a2a-protocol.org/latest/specification/#411-task) and [`Message`](https://a2a-protocol.org/latest/specification/#414-message) objects, providing continuity across a series of interactions.
**Generation and Assignment:**
  * Agents **MAY** generate a new `contextId` when processing a [`Message`](https://a2a-protocol.org/latest/specification/#414-message) that does not include a `contextId` field
  * If an agent generates a new `contextId`, it **MUST** be included in the response (either [`Task`](https://a2a-protocol.org/latest/specification/#411-task) or [`Message`](https://a2a-protocol.org/latest/specification/#414-message))
  * Agents **MAY** accept and preserve client-provided `contextId` values
  * If an agent cannot accept a client-provided `contextId`, it **MUST** reject the request with an error and **MUST NOT** generate a new `contextId` for the response
  * Clients **SHOULD NOT** provide a client-generated `contextId` to a server unless they understand how the server will process that `contextId`
  * Server-generated `contextId` values **SHOULD** be treated as opaque identifiers by clients


**Grouping and Scope:**
  * A `contextId` logically groups multiple [`Task`](https://a2a-protocol.org/latest/specification/#411-task) objects and [`Message`](https://a2a-protocol.org/latest/specification/#414-message) objects that are part of the same conversational context
  * All tasks and messages with the same `contextId` **SHOULD** be treated as part of the same conversational session
  * Agents **MAY** use the `contextId` to maintain internal state, conversational history, or LLM context across multiple interactions
  * Agents **MAY** implement context expiration or cleanup policies and **SHOULD** document any such policies


#### 3.4.2. Task Identifier Semantics[¶](https://a2a-protocol.org/latest/specification/#342-task-identifier-semantics "Permanent link")
A `taskId` is a unique identifier for a [`Task`](https://a2a-protocol.org/latest/specification/#411-task) object, representing a stateful unit of work with a defined lifecycle.
**Generation and Assignment:**
  * Task IDs are **server-generated** when a new task is created in response to a [`Message`](https://a2a-protocol.org/latest/specification/#414-message)
  * Agents **MUST** generate a unique `taskId` for each new task they create
  * The generated `taskId` **MUST** be included in the [`Task`](https://a2a-protocol.org/latest/specification/#411-task) object returned to the client
  * When a client includes a `taskId` in a [`Message`](https://a2a-protocol.org/latest/specification/#414-message), it **MUST** reference an existing task
  * Agents **MUST** return a [`TaskNotFoundError`](https://a2a-protocol.org/latest/specification/#332-error-handling) if the provided `taskId` does not correspond to an existing task
  * Client-provided `taskId` values for creating new tasks is **NOT** supported


#### 3.4.3. Multi-Turn Conversation Patterns[¶](https://a2a-protocol.org/latest/specification/#343-multi-turn-conversation-patterns "Permanent link")
The A2A protocol supports several patterns for multi-turn interactions:
**Context Continuity:**
  * [`Task`](https://a2a-protocol.org/latest/specification/#411-task) objects maintain conversation context through the `contextId` field
  * Clients **MAY** include the `contextId` in subsequent messages to indicate continuation of a previous interaction
  * Clients **MAY** use `taskId` (with or without `contextId`) to continue or refine a specific task
  * Clients **MAY** use `contextId` without `taskId` to start a new task within an existing conversation context
  * Agents **MUST** infer `contextId` from the task if only `taskId` is provided
  * Agents **MUST** reject messages containing mismatching `contextId` and `taskId` (i.e., the provided `contextId` is different from that of the referenced [`Task`](https://a2a-protocol.org/latest/specification/#411-task)).


**Input Required State:**
  * Agents can request additional input mid-processing by transitioning a task to the `input-required` state
  * The client continues the interaction by sending a new message with the same `taskId` and `contextId`


**Follow-up Messages:**
  * Clients can send additional messages with `taskId` references to continue or refine existing tasks
  * Clients **SHOULD** use the `referenceTaskIds` field in [`Message`](https://a2a-protocol.org/latest/specification/#414-message) to explicitly reference related tasks
  * Agents **SHOULD** use referenced tasks to understand the context and intent of follow-up requests


**Context Inheritance:**
  * New tasks created within the same `contextId` can inherit context from previous interactions
  * Agents **SHOULD** leverage the shared `contextId` to provide contextually relevant responses


### 3.5. Task Update Delivery Mechanisms[¶](https://a2a-protocol.org/latest/specification/#35-task-update-delivery-mechanisms "Permanent link")
The A2A protocol provides three complementary mechanisms for clients to receive updates about task progress and completion.
#### 3.5.1. Overview of Update Mechanisms[¶](https://a2a-protocol.org/latest/specification/#351-overview-of-update-mechanisms "Permanent link")
**Polling (Get Task):**
  * Client periodically calls Get Task ([Section 3.1.3](https://a2a-protocol.org/latest/specification/#313-get-task)) to check task status
  * Simple to implement, works with all protocol bindings
  * Higher latency, potential for unnecessary requests
  * Best for: Simple integrations, infrequent updates, clients behind restrictive firewalls


**Streaming:**
  * Real-time delivery of events as they occur
  * Operations: Stream Message ([Section 3.1.2](https://a2a-protocol.org/latest/specification/#312-send-streaming-message)) and Subscribe to Task ([Section 3.1.6](https://a2a-protocol.org/latest/specification/#316-subscribe-to-task))
  * Low latency, efficient for frequent updates
  * Requires persistent connection support
  * Best for: Interactive applications, real-time dashboards, live progress monitoring
  * Requires `AgentCard.capabilities.streaming` to be `true`


**Push Notifications (WebHooks):**
  * Agent sends HTTP POST requests to client-registered endpoints when task state changes
  * Client does not maintain persistent connection
  * Asynchronous delivery, client must be reachable via HTTP
  * Best for: Server-to-server integrations, long-running tasks, event-driven architectures
  * Operations: Create ([Section 3.1.7](https://a2a-protocol.org/latest/specification/#317-create-push-notification-config)), Get ([Section 3.1.8](https://a2a-protocol.org/latest/specification/#76-taskspushnotificationconfigget)), List ([Section 3.1.9](https://a2a-protocol.org/latest/specification/#319-list-push-notification-configs)), Delete ([Section 3.1.10](https://a2a-protocol.org/latest/specification/#3110-delete-push-notification-config))
  * Event types: TaskStatusUpdateEvent ([Section 4.2.1](https://a2a-protocol.org/latest/specification/#421-taskstatusupdateevent)), TaskArtifactUpdateEvent ([Section 4.2.2](https://a2a-protocol.org/latest/specification/#422-taskartifactupdateevent)), WebHook payloads ([Section 4.3](https://a2a-protocol.org/latest/specification/#43-push-notification-objects))
  * Requires `AgentCard.capabilities.pushNotifications` to be `true`
  * Regardless of the protocol binding being used by the agent, WebHook calls use plain HTTP and the JSON payloads as defined in the HTTP protocol binding


#### 3.5.2. Streaming Event Delivery[¶](https://a2a-protocol.org/latest/specification/#352-streaming-event-delivery "Permanent link")
**Event Ordering:**
All implementations MUST deliver events in the order they were generated. Events MUST NOT be reordered during transmission, regardless of protocol binding.
**Multiple Streams Per Task:**
An agent MAY serve multiple concurrent streams to one or more clients for the same task. This allows multiple clients (or the same client with multiple connections) to independently subscribe to and receive updates about a task's progress.
When multiple streams are active for a task:
  * Events MUST be broadcast to all active streams for that task
  * Each stream MUST receive the same events in the same order
  * Closing one stream MUST NOT affect other active streams for the same task
  * The task lifecycle is independent of any individual stream's lifecycle


This capability enables scenarios such as:
  * Multiple team members monitoring the same long-running task
  * A client reconnecting to a task after a network interruption by opening a new stream
  * Different applications or dashboards displaying real-time updates for the same task


#### 3.5.3. Push Notification Delivery[¶](https://a2a-protocol.org/latest/specification/#353-push-notification-delivery "Permanent link")
Push notifications are delivered via HTTP POST to client-registered webhook endpoints. The delivery semantics and reliability guarantees are defined in [Section 4.3](https://a2a-protocol.org/latest/specification/#43-push-notification-objects).
### 3.6 Versioning[¶](https://a2a-protocol.org/latest/specification/#36-versioning "Permanent link")
The specific version of the A2A protocol in use is identified using the `Major.Minor` elements (e.g. `1.0`) of the corresponding A2A specification version. Patch version numbers used by the specification, do not affect protocol compatibility. Patch version numbers SHOULD NOT be used in requests, responses and Agent Cards, and MUST not be considered when clients and servers negotiate protocol versions.
#### 3.6.1 Client Responsibilities[¶](https://a2a-protocol.org/latest/specification/#361-client-responsibilities "Permanent link")
Clients MUST send the `A2A-Version` header with each request to maintain compatibility after an agent upgrades to a new version of the protocol (except for 0.3 Clients - 0.3 will be assumed for empty header). Sending the `A2A-Version` header also provides visibility to agents about version usage in the ecosystem, which can help inform the risks of inplace version upgrades.
**Example of HTTP GET Request with Version Header:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-0-1)GET /tasks/task-123 HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-0-2)Host: agent.example.com
[](https://a2a-protocol.org/latest/specification/#__codelineno-0-3)A2A-Version: 1.0
[](https://a2a-protocol.org/latest/specification/#__codelineno-0-4)Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
[](https://a2a-protocol.org/latest/specification/#__codelineno-0-5)Accept: application/json

```

Clients MAY provide the `A2A-Version` as a request parameter instead of a header.
**Example of HTTP GET Request with Version request parameter:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-1-1)GET /tasks/task-123?A2A-Version=1.0 HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-1-2)Host: agent.example.com
[](https://a2a-protocol.org/latest/specification/#__codelineno-1-3)Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
[](https://a2a-protocol.org/latest/specification/#__codelineno-1-4)Accept: application/json

```

#### 3.6.2 Server Responsibilities[¶](https://a2a-protocol.org/latest/specification/#362-server-responsibilities "Permanent link")
Agents MUST process requests using the semantics of the requested `A2A-Version` (matching `Major.Minor`). If the version is not supported by the interface, agents MUST return a [`VersionNotSupportedError`](https://a2a-protocol.org/latest/specification/#332-error-handling).
Agents MUST interpret empty value as 0.3 version.
Agents CAN expose multiple interfaces for the same transport with different versions under the same or different URLs.
#### 3.6.3 Tooling support[¶](https://a2a-protocol.org/latest/specification/#363-tooling-support "Permanent link")
Tooling libraries and SDKs that implement the A2A protocol MUST provide mechanisms to help clients manage protocol versioning, such as negotiation of the transport and protocol version used. Client Agents that require the latest features of the protocol should be configured to request specific versions and avoid automatic fallback to older versions, to prevent silently losing functionality.
### 3.7 Messages and Artifacts[¶](https://a2a-protocol.org/latest/specification/#37-messages-and-artifacts "Permanent link")
Messages and Artifacts serve distinct purposes within the A2A protocol. The core interaction model defined by A2A is for clients to send messages to initiate a task that produces one or more artifacts.
Messages play several key roles:
  * **Task Initiation** : Clients send Messages to agents to initiate new tasks.
  * **Clarification Messages** : Agents may send Messages back to the client to request clarification prior to initiating a task.
  * **Status Messages** : Agents attach Messages to status update events to inform clients about task progress, request additional input, or provide informational updates.
  * **Task Interaction** : Clients send Messages to provide additional input or instructions for ongoing tasks.


Messages SHOULD NOT be used to deliver task outputs. Results SHOULD BE returned using Artifacts associated with a Task. This separation allows for a clear distinction between communication (Messages) and data output (Artifacts).
The Task History field contains Messages exchanged during task execution. However, not all Messages are guaranteed to be persisted in the Task history; for example, transient informational messages may not be stored. Messages exchanged prior to task creation may not be stored in Task history. The agent is responsible to determine which Messages are persisted in the Task History.
Clients using streaming to retrieve task updates MAY not receive all status update messages if the client is disconnected and then reconnects. Messages MUST NOT be considered a reliable delivery mechanism for critical information.
Agents MAY choose to persist all Messages that contain important information in the Task history to ensure clients can retrieve it later. However, clients MUST NOT rely on this behavior unless negotiated out-of-band.
## 4. Protocol Data Model[¶](https://a2a-protocol.org/latest/specification/#4-protocol-data-model "Permanent link")
The A2A protocol defines a canonical data model using Protocol Buffers. All protocol bindings **MUST** provide functionally equivalent representations of these data structures.
### 4.1. Core Objects[¶](https://a2a-protocol.org/latest/specification/#41-core-objects "Permanent link")
#### 4.1.1. Task[¶](https://a2a-protocol.org/latest/specification/#411-task "Permanent link")
`Task` is the core unit of action for A2A. It has a current status and when results are created for the task they are stored in the artifact. If there are multiple turns for a task, these are stored in history.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `id`  | `string`  | Yes  | Unique identifier (e.g. UUID) for the task, generated by the server for a new task.  |  
| `contextId`  | `string`  | No  | Unique identifier (e.g. UUID) for the contextual collection of interactions (tasks and messages).  |  
| `status`  | [`TaskStatus`](https://a2a-protocol.org/latest/specification/#taskstatus)  | Yes  | The current status of a `Task`, including `state` and a `message`.  |  
| `artifacts`  | array of [`Artifact`](https://a2a-protocol.org/latest/specification/#artifact)  | No  | A set of output artifacts for a `Task`.  |  
| `history`  | array of [`Message`](https://a2a-protocol.org/latest/specification/#message)  | No  | The history of interactions from a `Task`.  |  
| `metadata`  | `object`  | No  | A key/value object to store custom metadata about a task.  |  
#### 4.1.2. TaskStatus[¶](https://a2a-protocol.org/latest/specification/#412-taskstatus "Permanent link")
A container for the status of a task  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `state`  | [`TaskState`](https://a2a-protocol.org/latest/specification/#taskstate)  | Yes  | The current state of this task.  |  
| `message`  | [`Message`](https://a2a-protocol.org/latest/specification/#message)  | No  | A message associated with the status.  |  
| `timestamp`  | `timestamp`  | No  | ISO 8601 Timestamp when the status was recorded. Example: "2023-10-27T10:00:00Z"  |  
#### 4.1.3. TaskState[¶](https://a2a-protocol.org/latest/specification/#413-taskstate "Permanent link")
Defines the possible lifecycle states of a `Task`.  
| Value  | Description  |  
| --- | --- |  
| `TASK_STATE_UNSPECIFIED`  | The task is in an unknown or indeterminate state.  |  
| `TASK_STATE_SUBMITTED`  | Indicates that a task has been successfully submitted and acknowledged.  |  
| `TASK_STATE_WORKING`  | Indicates that a task is actively being processed by the agent.  |  
| `TASK_STATE_COMPLETED`  | Indicates that a task has finished successfully. This is a terminal state.  |  
| `TASK_STATE_FAILED`  | Indicates that a task has finished with an error. This is a terminal state.  |  
| `TASK_STATE_CANCELED`  | Indicates that a task was canceled before completion. This is a terminal state.  |  
| `TASK_STATE_INPUT_REQUIRED`  | Indicates that the agent requires additional user input to proceed. This is an interrupted state.  |  
| `TASK_STATE_REJECTED`  | Indicates that the agent has decided to not perform the task. This may be done during initial task creation or later once an agent has determined it can't or won't proceed. This is a terminal state.  |  
| `TASK_STATE_AUTH_REQUIRED`  | Indicates that authentication is required to proceed. This is an interrupted state.  |  
#### 4.1.4. Message[¶](https://a2a-protocol.org/latest/specification/#414-message "Permanent link")
`Message` is one unit of communication between client and server. It can be associated with a context and/or a task. For server messages, `context_id` must be provided, and `task_id` only if a task was created. For client messages, both fields are optional, with the caveat that if both are provided, they have to match (the `context_id` has to be the one that is set on the task). If only `task_id` is provided, the server will infer `context_id` from it.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `messageId`  | `string`  | Yes  | The unique identifier (e.g. UUID) of the message. This is created by the message creator.  |  
| `contextId`  | `string`  | No  | Optional. The context id of the message. If set, the message will be associated with the given context.  |  
| `taskId`  | `string`  | No  | Optional. The task id of the message. If set, the message will be associated with the given task.  |  
| `role`  | [`Role`](https://a2a-protocol.org/latest/specification/#role)  | Yes  | Identifies the sender of the message.  |  
| `parts`  | array of [`Part`](https://a2a-protocol.org/latest/specification/#part)  | Yes  | Parts is the container of the message content.  |  
| `metadata`  | `object`  | No  | Optional. Any metadata to provide along with the message.  |  
| `extensions`  | array of `string`  | No  | The URIs of extensions that are present or contributed to this Message.  |  
| `referenceTaskIds`  | array of `string`  | No  | A list of task IDs that this message references for additional context.  |  
#### 4.1.5. Role[¶](https://a2a-protocol.org/latest/specification/#415-role "Permanent link")
Defines the sender of a message in A2A protocol communication.  
| Value  | Description  |  
| --- | --- |  
| `ROLE_UNSPECIFIED`  | The role is unspecified.  |  
| `ROLE_USER`  | The message is from the client to the server.  |  
| `ROLE_AGENT`  | The message is from the server to the client.  |  
#### 4.1.6. Part[¶](https://a2a-protocol.org/latest/specification/#416-part "Permanent link")
`Part` represents a container for a section of communication content. Parts can be purely textual, some sort of file (image, video, etc) or a structured data blob (i.e. JSON).  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `text`  | `string`  | Optional (OneOf)  | The string content of the `text` part.  |  
| `raw`  | `bytes`  | Optional (OneOf)  | The `raw` byte content of a file. In JSON serialization, this is encoded as a base64 string.  |  
| `url`  | `string`  | Optional (OneOf)  | A `url` pointing to the file's content.  |  
| `data`  | `any`  | Optional (OneOf)  | Arbitrary structured `data` as a JSON value (object, array, string, number, boolean, or null).  |  
| `metadata`  | `object`  | No  | Optional. metadata associated with this part.  |  
| `filename`  | `string`  | No  | An optional `filename` for the file (e.g., "document.pdf").  |  
| `mediaType`  | `string`  | No  | The `media_type` (MIME type) of the part content (e.g., "text/plain", "application/json", "image/png"). This field is available for all part types.  |  
**Note:** A `Part` MUST contain exactly one of the following: `text`, `raw`, `url`, `data`
#### 4.1.7. Artifact[¶](https://a2a-protocol.org/latest/specification/#417-artifact "Permanent link")
Artifacts represent task outputs.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `artifactId`  | `string`  | Yes  | Unique identifier (e.g. UUID) for the artifact. It must be unique within a task.  |  
| `name`  | `string`  | No  | A human readable name for the artifact.  |  
| `description`  | `string`  | No  | Optional. A human readable description of the artifact.  |  
| `parts`  | array of [`Part`](https://a2a-protocol.org/latest/specification/#part)  | Yes  | The content of the artifact. Must contain at least one part.  |  
| `metadata`  | `object`  | No  | Optional. Metadata included with the artifact.  |  
| `extensions`  | array of `string`  | No  | The URIs of extensions that are present or contributed to this Artifact.  |  
### 4.2. Streaming Events[¶](https://a2a-protocol.org/latest/specification/#42-streaming-events "Permanent link")
#### 4.2.1. TaskStatusUpdateEvent[¶](https://a2a-protocol.org/latest/specification/#421-taskstatusupdateevent "Permanent link")
An event sent by the agent to notify the client of a change in a task's status.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `taskId`  | `string`  | Yes  | The ID of the task that has changed.  |  
| `contextId`  | `string`  | Yes  | The ID of the context that the task belongs to.  |  
| `status`  | [`TaskStatus`](https://a2a-protocol.org/latest/specification/#taskstatus)  | Yes  | The new status of the task.  |  
| `metadata`  | `object`  | No  | Optional. Metadata associated with the task update.  |  
#### 4.2.2. TaskArtifactUpdateEvent[¶](https://a2a-protocol.org/latest/specification/#422-taskartifactupdateevent "Permanent link")
A task delta where an artifact has been generated.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `taskId`  | `string`  | Yes  | The ID of the task for this artifact.  |  
| `contextId`  | `string`  | Yes  | The ID of the context that this task belongs to.  |  
| `artifact`  | [`Artifact`](https://a2a-protocol.org/latest/specification/#artifact)  | Yes  | The artifact that was generated or updated.  |  
| `append`  | `boolean`  | No  | If true, the content of this artifact should be appended to a previously sent artifact with the same ID.  |  
| `lastChunk`  | `boolean`  | No  | If true, this is the final chunk of the artifact.  |  
| `metadata`  | `object`  | No  | Optional. Metadata associated with the artifact update.  |  
### 4.3. Push Notification Objects[¶](https://a2a-protocol.org/latest/specification/#43-push-notification-objects "Permanent link")
#### 4.3.1. PushNotificationConfig[¶](https://a2a-protocol.org/latest/specification/#431-pushnotificationconfig "Permanent link")
**Error:** Message `PushNotificationConfig` not found.
#### 4.3.2. AuthenticationInfo[¶](https://a2a-protocol.org/latest/specification/#432-authenticationinfo "Permanent link")
Defines authentication details, used for push notifications.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `scheme`  | `string`  | Yes  | HTTP Authentication Scheme from the [IANA registry](https://www.iana.org/assignments/http-authschemes/). Examples: `Bearer`, `Basic`, `Digest`. Scheme names are case-insensitive per [RFC 9110 Section 11.1](https://www.rfc-editor.org/rfc/rfc9110#section-11.1).  |  
| `credentials`  | `string`  | No  | Push Notification credentials. Format depends on the scheme (e.g., token for Bearer).  |  
#### 4.3.3. Push Notification Payload[¶](https://a2a-protocol.org/latest/specification/#433-push-notification-payload "Permanent link")
When a task update occurs, the agent sends an HTTP POST request to the configured webhook URL. The payload uses the same [`StreamResponse`](https://a2a-protocol.org/latest/specification/#323-stream-response) format as streaming operations, allowing push notifications to deliver the same event types as real-time streams.
**Request Format:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-2-1)POST {webhook_url}
[](https://a2a-protocol.org/latest/specification/#__codelineno-2-2)Authorization: {authentication_scheme} {credentials}
[](https://a2a-protocol.org/latest/specification/#__codelineno-2-3)Content-Type: application/json
[](https://a2a-protocol.org/latest/specification/#__codelineno-2-4)
[](https://a2a-protocol.org/latest/specification/#__codelineno-2-5){
[](https://a2a-protocol.org/latest/specification/#__codelineno-2-6)  /* StreamResponse object - one of: */
[](https://a2a-protocol.org/latest/specification/#__codelineno-2-7)  "task": { /* Task object */ },
[](https://a2a-protocol.org/latest/specification/#__codelineno-2-8)  "message": { /* Message object */ },
[](https://a2a-protocol.org/latest/specification/#__codelineno-2-9)  "statusUpdate": { /* TaskStatusUpdateEvent object */ },
[](https://a2a-protocol.org/latest/specification/#__codelineno-2-10)  "artifactUpdate": { /* TaskArtifactUpdateEvent object */ }
[](https://a2a-protocol.org/latest/specification/#__codelineno-2-11)}

```

**Payload Structure:**
The webhook payload is a [`StreamResponse`](https://a2a-protocol.org/latest/specification/#323-stream-response) object containing exactly one of the following:
  * **task** : A [`Task`](https://a2a-protocol.org/latest/specification/#411-task) object with the current task state
  * **message** : A [`Message`](https://a2a-protocol.org/latest/specification/#414-message) object containing a message response
  * **statusUpdate** : A [`TaskStatusUpdateEvent`](https://a2a-protocol.org/latest/specification/#421-taskstatusupdateevent) indicating a status change
  * **artifactUpdate** : A [`TaskArtifactUpdateEvent`](https://a2a-protocol.org/latest/specification/#422-taskartifactupdateevent) indicating artifact updates


**Authentication:**
The agent MUST include authentication credentials in the request headers as specified in the [`PushNotificationConfig.authentication`](https://a2a-protocol.org/latest/specification/#432-authenticationinfo) field. The format follows standard HTTP authentication patterns (Bearer tokens, Basic auth, etc.).
**Client Responsibilities:**
  * Clients MUST respond with HTTP 2xx status codes to acknowledge successful receipt
  * Clients SHOULD process notifications idempotently, as duplicate deliveries may occur
  * Clients MUST validate the task ID matches an expected task
  * Clients SHOULD implement appropriate security measures to verify the notification source


**Server Guarantees:**
  * Agents MUST attempt delivery at least once for each configured webhook
  * Agents MAY implement retry logic with exponential backoff for failed deliveries
  * Agents SHOULD include a reasonable timeout for webhook requests (recommended: 10-30 seconds)
  * Agents MAY stop attempting delivery after a configured number of consecutive failures


For detailed security guidance on push notifications, see [Section 13.2 Push Notification Security](https://a2a-protocol.org/latest/specification/#132-push-notification-security).
### 4.4. Agent Discovery Objects[¶](https://a2a-protocol.org/latest/specification/#44-agent-discovery-objects "Permanent link")
#### 4.4.1. AgentCard[¶](https://a2a-protocol.org/latest/specification/#441-agentcard "Permanent link")
A self-describing manifest for an agent. It provides essential metadata including the agent's identity, capabilities, skills, supported communication methods, and security requirements.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `name`  | `string`  | Yes  | A human readable name for the agent. Example: "Recipe Agent"  |  
| `description`  | `string`  | Yes  | A human-readable description of the agent, assisting users and other agents in understanding its purpose. Example: "Agent that helps users with recipes and cooking."  |  
| `supportedInterfaces`  | array of [`AgentInterface`](https://a2a-protocol.org/latest/specification/#agentinterface)  | Yes  | Ordered list of supported interfaces. The first entry is preferred.  |  
| `provider`  | [`AgentProvider`](https://a2a-protocol.org/latest/specification/#agentprovider)  | No  | The service provider of the agent.  |  
| `version`  | `string`  | Yes  | The version of the agent. Example: "1.0.0"  |  
| `documentationUrl`  | `string`  | No  | A URL providing additional documentation about the agent.  |  
| `capabilities`  | [`AgentCapabilities`](https://a2a-protocol.org/latest/specification/#agentcapabilities)  | Yes  | A2A Capability set supported by the agent.  |  
| `securitySchemes`  | map of string to [`SecurityScheme`](https://a2a-protocol.org/latest/specification/#securityscheme)  | No  | The security scheme details used for authenticating with this agent.  |  
| `securityRequirements`  | array of [`SecurityRequirement`](https://a2a-protocol.org/latest/specification/#securityrequirement)  | No  | Security requirements for contacting the agent.  |  
| `defaultInputModes`  | array of `string`  | Yes  | The set of interaction modes that the agent supports across all skills. This can be overridden per skill. Defined as media types.  |  
| `defaultOutputModes`  | array of `string`  | Yes  | The media types supported as outputs from this agent.  |  
| `skills`  | array of [`AgentSkill`](https://a2a-protocol.org/latest/specification/#agentskill)  | Yes  | Skills represent the abilities of an agent. It is largely a descriptive concept but represents a more focused set of behaviors that the agent is likely to succeed at.  |  
| `signatures`  | array of [`AgentCardSignature`](https://a2a-protocol.org/latest/specification/#agentcardsignature)  | No  | JSON Web Signatures computed for this `AgentCard`.  |  
| `iconUrl`  | `string`  | No  | Optional. A URL to an icon for the agent.  |  
#### 4.4.2. AgentProvider[¶](https://a2a-protocol.org/latest/specification/#442-agentprovider "Permanent link")
Represents the service provider of an agent.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `url`  | `string`  | Yes  | A URL for the agent provider's website or relevant documentation. Example: "https://ai.google.dev"  |  
| `organization`  | `string`  | Yes  | The name of the agent provider's organization. Example: "Google"  |  
#### 4.4.3. AgentCapabilities[¶](https://a2a-protocol.org/latest/specification/#443-agentcapabilities "Permanent link")
Defines optional capabilities supported by an agent.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `streaming`  | `boolean`  | No  | Indicates if the agent supports streaming responses.  |  
| `pushNotifications`  | `boolean`  | No  | Indicates if the agent supports sending push notifications for asynchronous task updates.  |  
| `extensions`  | array of [`AgentExtension`](https://a2a-protocol.org/latest/specification/#agentextension)  | No  | A list of protocol extensions supported by the agent.  |  
| `extendedAgentCard`  | `boolean`  | No  | Indicates if the agent supports providing an extended agent card when authenticated.  |  
#### 4.4.4. AgentExtension[¶](https://a2a-protocol.org/latest/specification/#444-agentextension "Permanent link")
A declaration of a protocol extension supported by an Agent.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `uri`  | `string`  | No  | The unique URI identifying the extension.  |  
| `description`  | `string`  | No  | A human-readable description of how this agent uses the extension.  |  
| `required`  | `boolean`  | No  | If true, the client must understand and comply with the extension's requirements.  |  
| `params`  | `object`  | No  | Optional. Extension-specific configuration parameters.  |  
#### 4.4.5. AgentSkill[¶](https://a2a-protocol.org/latest/specification/#445-agentskill "Permanent link")
Represents a distinct capability or function that an agent can perform.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `id`  | `string`  | Yes  | A unique identifier for the agent's skill.  |  
| `name`  | `string`  | Yes  | A human-readable name for the skill.  |  
| `description`  | `string`  | Yes  | A detailed description of the skill.  |  
| `tags`  | array of `string`  | Yes  | A set of keywords describing the skill's capabilities.  |  
| `examples`  | array of `string`  | No  | Example prompts or scenarios that this skill can handle.  |  
| `inputModes`  | array of `string`  | No  | The set of supported input media types for this skill, overriding the agent's defaults.  |  
| `outputModes`  | array of `string`  | No  | The set of supported output media types for this skill, overriding the agent's defaults.  |  
| `securityRequirements`  | array of [`SecurityRequirement`](https://a2a-protocol.org/latest/specification/#securityrequirement)  | No  | Security schemes necessary for this skill.  |  
#### 4.4.6. AgentInterface[¶](https://a2a-protocol.org/latest/specification/#446-agentinterface "Permanent link")
Declares a combination of a target URL, transport and protocol version for interacting with the agent. This allows agents to expose the same functionality over multiple protocol binding mechanisms.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `url`  | `string`  | Yes  | The URL where this interface is available. Must be a valid absolute HTTPS URL in production. Example: "https://api.example.com/a2a/v1", "https://grpc.example.com/a2a"  |  
| `protocolBinding`  | `string`  | Yes  | The protocol binding supported at this URL. This is an open form string, to be easily extended for other protocol bindings. The core ones officially supported are `JSONRPC`, `GRPC` and `HTTP+JSON`.  |  
| `tenant`  | `string`  | No  | Tenant ID to be used in the request when calling the agent.  |  
| `protocolVersion`  | `string`  | Yes  | The version of the A2A protocol this interface exposes. Use the latest supported minor version per major version. Examples: "0.3", "1.0"  |  
#### 4.4.7. AgentCardSignature[¶](https://a2a-protocol.org/latest/specification/#447-agentcardsignature "Permanent link")
AgentCardSignature represents a JWS signature of an AgentCard. This follows the JSON format of an RFC 7515 JSON Web Signature (JWS).  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `protected`  | `string`  | Yes  | Required. The protected JWS header for the signature. This is always a base64url-encoded JSON object.  |  
| `signature`  | `string`  | Yes  | Required. The computed signature, base64url-encoded.  |  
| `header`  | `object`  | No  | The unprotected JWS header values.  |  
### 4.5. Security Objects[¶](https://a2a-protocol.org/latest/specification/#45-security-objects "Permanent link")
#### 4.5.1. SecurityScheme[¶](https://a2a-protocol.org/latest/specification/#451-securityscheme "Permanent link")
Defines a security scheme that can be used to secure an agent's endpoints. This is a discriminated union type based on the OpenAPI 3.2 Security Scheme Object. See: https://spec.openapis.org/oas/v3.2.0.html#security-scheme-object  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `apiKeySecurityScheme`  | [`APIKeySecurityScheme`](https://a2a-protocol.org/latest/specification/#apikeysecurityscheme)  | Optional (OneOf)  | API key-based authentication.  |  
| `httpAuthSecurityScheme`  | [`HTTPAuthSecurityScheme`](https://a2a-protocol.org/latest/specification/#httpauthsecurityscheme)  | Optional (OneOf)  | HTTP authentication (Basic, Bearer, etc.).  |  
| `oauth2SecurityScheme`  | [`OAuth2SecurityScheme`](https://a2a-protocol.org/latest/specification/#oauth2securityscheme)  | Optional (OneOf)  | OAuth 2.0 authentication.  |  
| `openIdConnectSecurityScheme`  | [`OpenIdConnectSecurityScheme`](https://a2a-protocol.org/latest/specification/#openidconnectsecurityscheme)  | Optional (OneOf)  | OpenID Connect authentication.  |  
| `mtlsSecurityScheme`  | [`MutualTlsSecurityScheme`](https://a2a-protocol.org/latest/specification/#mutualtlssecurityscheme)  | Optional (OneOf)  | Mutual TLS authentication.  |  
**Note:** A `SecurityScheme` MUST contain exactly one of the following: `apiKeySecurityScheme`, `httpAuthSecurityScheme`, `oauth2SecurityScheme`, `openIdConnectSecurityScheme`, `mtlsSecurityScheme`
#### 4.5.2. APIKeySecurityScheme[¶](https://a2a-protocol.org/latest/specification/#452-apikeysecurityscheme "Permanent link")
Defines a security scheme using an API key.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `description`  | `string`  | No  | An optional description for the security scheme.  |  
| `location`  | `string`  | Yes  | The location of the API key. Valid values are "query", "header", or "cookie".  |  
| `name`  | `string`  | Yes  | The name of the header, query, or cookie parameter to be used.  |  
#### 4.5.3. HTTPAuthSecurityScheme[¶](https://a2a-protocol.org/latest/specification/#453-httpauthsecurityscheme "Permanent link")
Defines a security scheme using HTTP authentication.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `description`  | `string`  | No  | An optional description for the security scheme.  |  
| `scheme`  | `string`  | Yes  | The name of the HTTP Authentication scheme to be used in the Authorization header, as defined in RFC7235 (e.g., "Bearer"). This value should be registered in the IANA Authentication Scheme registry.  |  
| `bearerFormat`  | `string`  | No  | A hint to the client to identify how the bearer token is formatted (e.g., "JWT"). Primarily for documentation purposes.  |  
#### 4.5.4. OAuth2SecurityScheme[¶](https://a2a-protocol.org/latest/specification/#454-oauth2securityscheme "Permanent link")
Defines a security scheme using OAuth 2.0.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `description`  | `string`  | No  | An optional description for the security scheme.  |  
| `flows`  | [`OAuthFlows`](https://a2a-protocol.org/latest/specification/#oauthflows)  | Yes  | An object containing configuration information for the supported OAuth 2.0 flows.  |  
| `oauth2MetadataUrl`  | `string`  | No  | URL to the OAuth2 authorization server metadata [RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414). TLS is required.  |  
#### 4.5.5. OpenIdConnectSecurityScheme[¶](https://a2a-protocol.org/latest/specification/#455-openidconnectsecurityscheme "Permanent link")
Defines a security scheme using OpenID Connect.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `description`  | `string`  | No  | An optional description for the security scheme.  |  
| `openIdConnectUrl`  | `string`  | Yes  | The [OpenID Connect Discovery URL](https://openid.net/specs/openid-connect-discovery-1_0.html) for the OIDC provider's metadata.  |  
#### 4.5.6. MutualTlsSecurityScheme[¶](https://a2a-protocol.org/latest/specification/#456-mutualtlssecurityscheme "Permanent link")
Defines a security scheme using mTLS authentication.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `description`  | `string`  | No  | An optional description for the security scheme.  |  
#### 4.5.7. OAuthFlows[¶](https://a2a-protocol.org/latest/specification/#457-oauthflows "Permanent link")
Defines the configuration for the supported OAuth 2.0 flows.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `authorizationCode`  | [`AuthorizationCodeOAuthFlow`](https://a2a-protocol.org/latest/specification/#authorizationcodeoauthflow)  | Optional (OneOf)  | Configuration for the OAuth Authorization Code flow.  |  
| `clientCredentials`  | [`ClientCredentialsOAuthFlow`](https://a2a-protocol.org/latest/specification/#clientcredentialsoauthflow)  | Optional (OneOf)  | Configuration for the OAuth Client Credentials flow.  |  
| `implicit`  | [`ImplicitOAuthFlow`](https://a2a-protocol.org/latest/specification/#implicitoauthflow)  | Optional (OneOf)  | Deprecated: Use Authorization Code + PKCE instead.  |  
| `password`  | [`PasswordOAuthFlow`](https://a2a-protocol.org/latest/specification/#passwordoauthflow)  | Optional (OneOf)  | Deprecated: Use Authorization Code + PKCE or Device Code.  |  
| `deviceCode`  | [`DeviceCodeOAuthFlow`](https://a2a-protocol.org/latest/specification/#devicecodeoauthflow)  | Optional (OneOf)  | Configuration for the OAuth Device Code flow.  |  
**Note:** A `OAuthFlows` MUST contain exactly one of the following: `authorizationCode`, `clientCredentials`, `implicit`, `password`, `deviceCode`
#### 4.5.8. AuthorizationCodeOAuthFlow[¶](https://a2a-protocol.org/latest/specification/#458-authorizationcodeoauthflow "Permanent link")
Defines configuration details for the OAuth 2.0 Authorization Code flow.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `authorizationUrl`  | `string`  | Yes  | The authorization URL to be used for this flow.  |  
| `tokenUrl`  | `string`  | Yes  | The token URL to be used for this flow.  |  
| `refreshUrl`  | `string`  | No  | The URL to be used for obtaining refresh tokens.  |  
| `scopes`  | map of string to `string`  | Yes  | The available scopes for the OAuth2 security scheme.  |  
| `pkceRequired`  | `boolean`  | No  | Indicates if PKCE (RFC 7636) is required for this flow. PKCE should always be used for public clients and is recommended for all clients.  |  
#### 4.5.9. ClientCredentialsOAuthFlow[¶](https://a2a-protocol.org/latest/specification/#459-clientcredentialsoauthflow "Permanent link")
Defines configuration details for the OAuth 2.0 Client Credentials flow.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tokenUrl`  | `string`  | Yes  | The token URL to be used for this flow.  |  
| `refreshUrl`  | `string`  | No  | The URL to be used for obtaining refresh tokens.  |  
| `scopes`  | map of string to `string`  | Yes  | The available scopes for the OAuth2 security scheme.  |  
#### 4.5.10. DeviceCodeOAuthFlow[¶](https://a2a-protocol.org/latest/specification/#4510-devicecodeoauthflow "Permanent link")
Defines configuration details for the OAuth 2.0 Device Code flow (RFC 8628). This flow is designed for input-constrained devices such as IoT devices, and CLI tools where the user authenticates on a separate device.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `deviceAuthorizationUrl`  | `string`  | Yes  | The device authorization endpoint URL.  |  
| `tokenUrl`  | `string`  | Yes  | The token URL to be used for this flow.  |  
| `refreshUrl`  | `string`  | No  | The URL to be used for obtaining refresh tokens.  |  
| `scopes`  | map of string to `string`  | Yes  | The available scopes for the OAuth2 security scheme.  |  
### 4.6. Extensions[¶](https://a2a-protocol.org/latest/specification/#46-extensions "Permanent link")
The A2A protocol supports extensions to provide additional functionality or data beyond the core specification while maintaining backward compatibility and interoperability. Extensions allow agents to declare additional capabilities such as protocol enhancements or vendor-specific features, maintain compatibility with clients that don't support specific extensions, enable innovation through experimental or domain-specific features without modifying the core protocol, and facilitate standardization by providing a pathway for community-developed features to become part of the core specification.
#### 4.6.1. Extension Declaration[¶](https://a2a-protocol.org/latest/specification/#461-extension-declaration "Permanent link")
Agents declare their supported extensions in the [`AgentCard`](https://a2a-protocol.org/latest/specification/#441-agentcard) using the `extensions` field, which contains an array of [`AgentExtension`](https://a2a-protocol.org/latest/specification/#444-agentextension) objects.
_Example: Agent declaring extension support in AgentCard:_

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-2)  "name": "Research Assistant Agent",
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-3)  "description": "AI agent for academic research and fact-checking",
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-4)  "supportedInterfaces": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-5)    {
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-6)      "url": "https://research-agent.example.com/a2a/v1",
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-7)      "protocolBinding": "HTTP+JSON",
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-8)      "protocolVersion": "0.3",
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-9)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-10)  ],
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-11)  "capabilities": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-12)    "streaming": false,
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-13)    "pushNotifications": false,
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-14)    "extensions": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-15)      {
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-16)        "uri": "https://standards.org/extensions/citations/v1",
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-17)        "description": "Provides citation formatting and source verification",
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-18)        "required": false
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-19)      },
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-20)      {
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-21)        "uri": "https://example.com/extensions/geolocation/v1",
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-22)        "description": "Location-based search capabilities",
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-23)        "required": false
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-24)      }
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-25)    ]
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-26)  },
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-27)  "defaultInputModes": ["text/plain"],
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-28)  "defaultOutputModes": ["text/plain"],
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-29)  "skills": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-30)    {
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-31)      "id": "academic-research",
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-32)      "name": "Academic Research Assistant",
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-33)      "description": "Provides research assistance with citations and source verification",
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-34)      "tags": ["research", "citations", "academic"],
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-35)      "examples": ["Find peer-reviewed articles on climate change"],
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-36)      "inputModes": ["text/plain"],
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-37)      "outputModes": ["text/plain"]
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-38)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-39)  ]
[](https://a2a-protocol.org/latest/specification/#__codelineno-3-40)}

```

Clients indicate their desire to opt into the use of specific extensions through binding-specific mechanisms such as HTTP headers, gRPC metadata, or JSON-RPC request parameters that identify the extension identifiers they wish to utilize during the interaction.
_Example: HTTP client opting into extensions using headers:_

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-4-1)POST /message:send HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-4-2)Host: agent.example.com
[](https://a2a-protocol.org/latest/specification/#__codelineno-4-3)Content-Type: application/json
[](https://a2a-protocol.org/latest/specification/#__codelineno-4-4)Authorization: Bearer token
[](https://a2a-protocol.org/latest/specification/#__codelineno-4-5)A2A-Extensions: https://example.com/extensions/geolocation/v1,https://standards.org/extensions/citations/v1
[](https://a2a-protocol.org/latest/specification/#__codelineno-4-6)
[](https://a2a-protocol.org/latest/specification/#__codelineno-4-7){
[](https://a2a-protocol.org/latest/specification/#__codelineno-4-8)  "message": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-4-9)    "role": "ROLE_USER",
[](https://a2a-protocol.org/latest/specification/#__codelineno-4-10)    "parts": [{"text": "Find restaurants near me"}],
[](https://a2a-protocol.org/latest/specification/#__codelineno-4-11)    "extensions": ["https://example.com/extensions/geolocation/v1"],
[](https://a2a-protocol.org/latest/specification/#__codelineno-4-12)    "metadata": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-4-13)      "https://example.com/extensions/geolocation/v1": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-4-14)        "latitude": 37.7749,
[](https://a2a-protocol.org/latest/specification/#__codelineno-4-15)        "longitude": -122.4194
[](https://a2a-protocol.org/latest/specification/#__codelineno-4-16)      }
[](https://a2a-protocol.org/latest/specification/#__codelineno-4-17)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-4-18)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-4-19)}

```

#### 4.6.2. Extensions Points[¶](https://a2a-protocol.org/latest/specification/#462-extensions-points "Permanent link")
Extensions can be integrated into the A2A protocol at several well-defined extension points:
**Message Extensions:**
Messages can be extended to allow clients to provide additional strongly typed context or parameters relevant to the message being sent, or TaskStatus Messages to include extra information about the task's progress.
_Example: A location extension using the extensions and metadata arrays:_

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-5-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-5-2)  "role": "ROLE_USER",
[](https://a2a-protocol.org/latest/specification/#__codelineno-5-3)  "parts": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-5-4)    {"text": "Find restaurants near me"}
[](https://a2a-protocol.org/latest/specification/#__codelineno-5-5)  ],
[](https://a2a-protocol.org/latest/specification/#__codelineno-5-6)  "extensions": ["https://example.com/extensions/geolocation/v1"],
[](https://a2a-protocol.org/latest/specification/#__codelineno-5-7)  "metadata": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-5-8)    "https://example.com/extensions/geolocation/v1": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-5-9)      "latitude": 37.7749,
[](https://a2a-protocol.org/latest/specification/#__codelineno-5-10)      "longitude": -122.4194,
[](https://a2a-protocol.org/latest/specification/#__codelineno-5-11)      "accuracy": 10.0,
[](https://a2a-protocol.org/latest/specification/#__codelineno-5-12)      "timestamp": "2025-10-21T14:30:00Z"
[](https://a2a-protocol.org/latest/specification/#__codelineno-5-13)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-5-14)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-5-15)}

```

**Artifact Extensions:**
Artifacts can include extension data to provide strongly typed context or metadata about the generated content.
_Example: An artifact with citation extension for research sources:_

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-2)  "artifactId": "research-summary-001",
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-3)  "name": "Climate Change Summary",
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-4)  "parts": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-5)    {
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-6)      "text": "Global temperatures have risen by 1.1°C since pre-industrial times, with significant impacts on weather patterns and sea levels."
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-7)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-8)  ],
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-9)  "extensions": ["https://standards.org/extensions/citations/v1"],
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-10)  "metadata": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-11)    "https://standards.org/extensions/citations/v1": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-12)      "sources": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-13)        {
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-14)          "title": "Global Temperature Anomalies - 2023 Report",
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-15)          "authors": ["Smith, J.", "Johnson, M."],
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-16)          "url": "https://climate.gov/reports/2023-temperature",
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-17)          "accessDate": "2025-10-21",
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-18)          "relevantText": "Global temperatures have risen by 1.1°C"
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-19)        }
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-20)      ]
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-21)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-22)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-6-23)}

```

#### 4.6.3. Extension Versioning and Compatibility[¶](https://a2a-protocol.org/latest/specification/#463-extension-versioning-and-compatibility "Permanent link")
Extensions **SHOULD** include version information in their URI identifier. This allows clients and agents to negotiate compatible versions of extensions during interactions. A new URI **MUST** be created for breaking changes to an extension.
If a client requests a versions of an extension that the agent does not support, the agent **SHOULD** ignore the extension for that interaction and proceed without it, unless the extension is marked as `required` in the AgentCard, in which case the agent **MUST** return an error indicating unsupported extension. It **MUST NOT** fall back to a previous version of the extension automatically.
## 5. Protocol Binding Requirements and Interoperability[¶](https://a2a-protocol.org/latest/specification/#5-protocol-binding-requirements-and-interoperability "Permanent link")
### 5.1. Functional Equivalence Requirements[¶](https://a2a-protocol.org/latest/specification/#51-functional-equivalence-requirements "Permanent link")
When an agent supports multiple protocols, all supported protocols **MUST** :
  * **Identical Functionality** : Provide the same set of operations and capabilities
  * **Consistent Behavior** : Return semantically equivalent results for the same requests
  * **Same Error Handling** : Map errors consistently using appropriate protocol-specific codes
  * **Equivalent Authentication** : Support the same authentication schemes declared in the AgentCard


### 5.2. Protocol Selection and Negotiation[¶](https://a2a-protocol.org/latest/specification/#52-protocol-selection-and-negotiation "Permanent link")
  * **Agent Declaration** : Agents **MUST** declare all supported protocols in their AgentCard
  * **Client Choice** : Clients **MAY** choose any protocol declared by the agent
  * **Fallback Behavior** : Clients **SHOULD** implement fallback logic for alternative protocols


### 5.3. Method Mapping Reference[¶](https://a2a-protocol.org/latest/specification/#53-method-mapping-reference "Permanent link")  
| Functionality  | JSON-RPC Method  | gRPC Method  | REST Endpoint  |  
| --- | --- | --- | --- |  
| Send message  | `SendMessage`  | `SendMessage`  | `POST /message:send`  |  
| Stream message  | `SendStreamingMessage`  | `SendStreamingMessage`  | `POST /message:stream`  |  
| Get task  | `GetTask`  | `GetTask`  | `GET /tasks/{id}`  |  
| List tasks  | `ListTasks`  | `ListTasks`  | `GET /tasks`  |  
| Cancel task  | `CancelTask`  | `CancelTask`  | `POST /tasks/{id}:cancel`  |  
| Subscribe to task  | `SubscribeToTask`  | `SubscribeToTask`  | `POST /tasks/{id}:subscribe`  |  
| Create push notification config  | `CreateTaskPushNotificationConfig`  | `CreateTaskPushNotificationConfig`  | `POST /tasks/{id}/pushNotificationConfigs`  |  
| Get push notification config  | `GetTaskPushNotificationConfig`  | `GetTaskPushNotificationConfig`  | `GET /tasks/{id}/pushNotificationConfigs/{configId}`  |  
| List push notification configs  | `ListTaskPushNotificationConfigs`  | `ListTaskPushNotificationConfigs`  | `GET /tasks/{id}/pushNotificationConfigs`  |  
| Delete push notification config  | `DeleteTaskPushNotificationConfig`  | `DeleteTaskPushNotificationConfig`  | `DELETE /tasks/{id}/pushNotificationConfigs/{configId}`  |  
| Get extended Agent Card  | `GetExtendedAgentCard`  | `GetExtendedAgentCard`  | `GET /extendedAgentCard`  |  
### 5.4. Error Code Mappings[¶](https://a2a-protocol.org/latest/specification/#54-error-code-mappings "Permanent link")
All A2A-specific errors defined in [Section 3.3.2](https://a2a-protocol.org/latest/specification/#332-error-handling) **MUST** be mapped to binding-specific error representations. The following table provides the canonical mappings for each standard protocol binding:  
| A2A Error Type  | JSON-RPC Code  | gRPC Status  | HTTP Status  |  
| --- | --- | --- | --- |  
| `TaskNotFoundError`  | `-32001`  | `NOT_FOUND`  | `404 Not Found`  |  
| `TaskNotCancelableError`  | `-32002`  | `FAILED_PRECONDITION`  | `409 Conflict`  |  
| `PushNotificationNotSupportedError`  | `-32003`  | `UNIMPLEMENTED`  | `400 Bad Request`  |  
| `UnsupportedOperationError`  | `-32004`  | `UNIMPLEMENTED`  | `400 Bad Request`  |  
| `ContentTypeNotSupportedError`  | `-32005`  | `INVALID_ARGUMENT`  | `415 Unsupported Media Type`  |  
| `InvalidAgentResponseError`  | `-32006`  | `INTERNAL`  | `502 Bad Gateway`  |  
| `ExtendedAgentCardNotConfiguredError`  | `-32007`  | `FAILED_PRECONDITION`  | `400 Bad Request`  |  
| `ExtensionSupportRequiredError`  | `-32008`  | `FAILED_PRECONDITION`  | `400 Bad Request`  |  
| `VersionNotSupportedError`  | `-32009`  | `UNIMPLEMENTED`  | `400 Bad Request`  |  
**Custom Binding Requirements:**
Custom protocol bindings **MUST** define equivalent error code mappings that preserve the semantic meaning of each A2A error type. The binding specification **SHOULD** provide a similar mapping table showing how each A2A error type is represented in the custom binding's native error format.
For binding-specific error structures and examples, see:
  * [JSON-RPC Error Handling](https://a2a-protocol.org/latest/specification/#95-error-handling)
  * [gRPC Error Handling](https://a2a-protocol.org/latest/specification/#106-error-handling)
  * [HTTP/REST Error Handling](https://a2a-protocol.org/latest/specification/#116-error-handling)


### 5.5. JSON Field Naming Convention[¶](https://a2a-protocol.org/latest/specification/#55-json-field-naming-convention "Permanent link")
All JSON serializations of the A2A protocol data model **MUST** use **camelCase** naming for field names, not the snake_case convention used in Protocol Buffer definitions.
**Naming Convention:**
  * Protocol Buffer field: `protocol_version` ? JSON field: `protocolVersion`
  * Protocol Buffer field: `context_id` ? JSON field: `contextId`
  * Protocol Buffer field: `default_input_modes` ? JSON field: `defaultInputModes`
  * Protocol Buffer field: `push_notification_config` ? JSON field: `pushNotificationConfig`


**Enum Values:**
  * Enum values **MUST** be represented according to the [ProtoJSON specification](https://protobuf.dev/programming-guides/json/), which serializes enums as their string names **as defined in the Protocol Buffer definition** (typically SCREAMING_SNAKE_CASE).


**Examples:**
  * Protocol Buffer enum: `TASK_STATE_INPUT_REQUIRED` ? JSON value: `"TASK_STATE_INPUT_REQUIRED"`
  * Protocol Buffer enum: `ROLE_USER` ? JSON value: `"ROLE_USER"`


**Note:** This follows the ProtoJSON specification as adopted in [ADR-001](https://a2a-protocol.org/latest/adrs/adr-001-protojson-serialization.md).
### 5.6. Data Type Conventions[¶](https://a2a-protocol.org/latest/specification/#56-data-type-conventions "Permanent link")
This section documents conventions for common data types used throughout the A2A protocol, particularly as they apply to protocol bindings.
#### 5.6.1. Timestamps[¶](https://a2a-protocol.org/latest/specification/#561-timestamps "Permanent link")
The A2A protocol uses [`google.protobuf.Timestamp`](https://protobuf.dev/reference/protobuf/google.protobuf/#timestamp) for all timestamp fields in the Protocol Buffer definitions. When serialized to JSON (in JSON-RPC, HTTP/REST, or other JSON-based bindings), these timestamps **MUST** be represented as ISO 8601 formatted strings in UTC timezone.
**Format Requirements:**
  * **Format:** ISO 8601 combined date and time representation
  * **Timezone:** UTC (denoted by 'Z' suffix)
  * **Precision:** Millisecond precision **SHOULD** be used where available
  * **Pattern:** `YYYY-MM-DDTHH:mm:ss.sssZ`


**Examples:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-7-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-7-2)  "timestamp": "2025-10-28T10:30:00.000Z",
[](https://a2a-protocol.org/latest/specification/#__codelineno-7-3)  "createdAt": "2025-10-28T14:25:33.142Z",
[](https://a2a-protocol.org/latest/specification/#__codelineno-7-4)  "lastModified": "2025-10-31T17:45:22.891Z"
[](https://a2a-protocol.org/latest/specification/#__codelineno-7-5)}

```

**Implementation Notes:**
  * Protocol Buffer's `google.protobuf.Timestamp` represents time as seconds since Unix epoch (January 1, 1970, 00:00:00 UTC) plus nanoseconds
  * JSON serialization automatically converts this to ISO 8601 format when using standard Protocol Buffer JSON encoding
  * Clients and servers **MUST** parse and generate ISO 8601 timestamps correctly
  * When millisecond precision is not available, the fractional seconds portion **MAY** be omitted or zero-filled
  * Timestamps **MUST NOT** include timezone offsets other than 'Z' (all times are UTC)


### 5.7. Field Presence and Optionality[¶](https://a2a-protocol.org/latest/specification/#57-field-presence-and-optionality "Permanent link")
The Protocol Buffer definition in `specification/a2a.proto` uses [`google.api.field_behavior`](https://github.com/googleapis/googleapis/blob/master/google/api/field_behavior.proto) annotations to indicate whether fields are `REQUIRED`. These annotations serve as both documentation and validation hints for implementations.
**Required Fields:**
Fields marked with `[(google.api.field_behavior) = REQUIRED]` indicate that the field **MUST** be present and set in valid messages. Implementations **SHOULD** validate these requirements and reject messages with missing required fields. Arrays marked as required **MUST** contain at least one element.
**Optional Field Presence:**
The Protocol Buffer `optional` keyword is used to distinguish between a field being explicitly set versus omitted. This distinction is critical for two scenarios:
  1. **Explicit Default Values:** Some fields in the specification define default values that differ from Protocol Buffer's implicit defaults. Implementations should apply the default value when the field is not explicitly provided.
  2. **Agent Card Canonicalization:** When creating cryptographic signatures of Agent Cards, it is required to produce a canonical JSON representation. The `optional` keyword enables implementations to distinguish between fields that were explicitly set (and should be included in the canonical form) versus fields that were omitted (and should be excluded from canonicalization). This ensures Agent Cards can be reconstructed to accurately match their signature.


**Unrecognized Fields:**
Implementations **SHOULD** ignore unrecognized fields in messages, allowing for forward compatibility as the protocol evolves.
## 6. Common Workflows & Examples[¶](https://a2a-protocol.org/latest/specification/#6-common-workflows-examples "Permanent link")
This section provides illustrative examples of common A2A interactions across different bindings.
### 6.1. Basic Task Execution[¶](https://a2a-protocol.org/latest/specification/#61-basic-task-execution "Permanent link")
**Scenario:** Client asks a question and receives a completed task response.
**Request:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-8-1)POST /message:send HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-8-2)Host: agent.example.com
[](https://a2a-protocol.org/latest/specification/#__codelineno-8-3)Content-Type: application/a2a+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-8-4)Authorization: Bearer token
[](https://a2a-protocol.org/latest/specification/#__codelineno-8-5)
[](https://a2a-protocol.org/latest/specification/#__codelineno-8-6){
[](https://a2a-protocol.org/latest/specification/#__codelineno-8-7)  "message": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-8-8)    "role": "ROLE_USER",
[](https://a2a-protocol.org/latest/specification/#__codelineno-8-9)    "parts": [{"text": "What is the weather today?"}],
[](https://a2a-protocol.org/latest/specification/#__codelineno-8-10)    "messageId": "msg-uuid"
[](https://a2a-protocol.org/latest/specification/#__codelineno-8-11)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-8-12)}

```

**Response:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-9-1)HTTP/1.1 200 OK
[](https://a2a-protocol.org/latest/specification/#__codelineno-9-2)Content-Type: application/a2a+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-9-3)
[](https://a2a-protocol.org/latest/specification/#__codelineno-9-4){
[](https://a2a-protocol.org/latest/specification/#__codelineno-9-5)  "task": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-9-6)    "id": "task-uuid",
[](https://a2a-protocol.org/latest/specification/#__codelineno-9-7)    "contextId": "context-uuid",
[](https://a2a-protocol.org/latest/specification/#__codelineno-9-8)    "status": {"state": "TASK_STATE_COMPLETED"},
[](https://a2a-protocol.org/latest/specification/#__codelineno-9-9)    "artifacts": [{
[](https://a2a-protocol.org/latest/specification/#__codelineno-9-10)      "artifactId": "artifact-uuid",
[](https://a2a-protocol.org/latest/specification/#__codelineno-9-11)      "name": "Weather Report",
[](https://a2a-protocol.org/latest/specification/#__codelineno-9-12)      "parts": [{"text": "Today will be sunny with a high of 75°F"}]
[](https://a2a-protocol.org/latest/specification/#__codelineno-9-13)    }]
[](https://a2a-protocol.org/latest/specification/#__codelineno-9-14)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-9-15)}

```

### 6.2. Streaming Task Execution[¶](https://a2a-protocol.org/latest/specification/#62-streaming-task-execution "Permanent link")
**Scenario:** Client requests a long-running task with real-time updates.
**Request:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-10-1)POST /message:stream HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-10-2)Host: agent.example.com
[](https://a2a-protocol.org/latest/specification/#__codelineno-10-3)Content-Type: application/a2a+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-10-4)Authorization: Bearer token
[](https://a2a-protocol.org/latest/specification/#__codelineno-10-5)
[](https://a2a-protocol.org/latest/specification/#__codelineno-10-6){
[](https://a2a-protocol.org/latest/specification/#__codelineno-10-7)  "message": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-10-8)    "role": "ROLE_USER",
[](https://a2a-protocol.org/latest/specification/#__codelineno-10-9)    "parts": [{"text": "Write a detailed report on climate change"}],
[](https://a2a-protocol.org/latest/specification/#__codelineno-10-10)    "messageId": "msg-uuid"
[](https://a2a-protocol.org/latest/specification/#__codelineno-10-11)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-10-12)}

```

**SSE Response Stream:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-11-1)HTTP/1.1 200 OK
[](https://a2a-protocol.org/latest/specification/#__codelineno-11-2)Content-Type: text/event-stream
[](https://a2a-protocol.org/latest/specification/#__codelineno-11-3)
[](https://a2a-protocol.org/latest/specification/#__codelineno-11-4)data: {"task": {"id": "task-uuid", "status": {"state": "TASK_STATE_WORKING"}}}
[](https://a2a-protocol.org/latest/specification/#__codelineno-11-5)
[](https://a2a-protocol.org/latest/specification/#__codelineno-11-6)data: {"artifactUpdate": {"taskId": "task-uuid", "artifact": {"parts": [{"text": "# Climate Change Report\n\n"}]}}}
[](https://a2a-protocol.org/latest/specification/#__codelineno-11-7)
[](https://a2a-protocol.org/latest/specification/#__codelineno-11-8)data: {"statusUpdate": {"taskId": "task-uuid", "status": {"state": "TASK_STATE_COMPLETED"}}}

```

### 6.3. Multi-Turn Interaction[¶](https://a2a-protocol.org/latest/specification/#63-multi-turn-interaction "Permanent link")
**Scenario:** Agent requires additional input to complete a task.
**Initial Request:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-12-1)POST /message:send HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-12-2)Host: agent.example.com
[](https://a2a-protocol.org/latest/specification/#__codelineno-12-3)Content-Type: application/a2a+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-12-4)Authorization: Bearer token
[](https://a2a-protocol.org/latest/specification/#__codelineno-12-5)
[](https://a2a-protocol.org/latest/specification/#__codelineno-12-6){
[](https://a2a-protocol.org/latest/specification/#__codelineno-12-7)  "message": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-12-8)    "role": "ROLE_USER",
[](https://a2a-protocol.org/latest/specification/#__codelineno-12-9)    "parts": [{"text": "Book me a flight"}],
[](https://a2a-protocol.org/latest/specification/#__codelineno-12-10)    "messageId": "msg-1"
[](https://a2a-protocol.org/latest/specification/#__codelineno-12-11)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-12-12)}

```

**Response (Input Required):**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-13-1)HTTP/1.1 200 OK
[](https://a2a-protocol.org/latest/specification/#__codelineno-13-2)Content-Type: application/a2a+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-13-3)
[](https://a2a-protocol.org/latest/specification/#__codelineno-13-4){
[](https://a2a-protocol.org/latest/specification/#__codelineno-13-5)  "task": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-13-6)    "id": "task-uuid",
[](https://a2a-protocol.org/latest/specification/#__codelineno-13-7)    "status": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-13-8)      "state": "TASK_STATE_INPUT_REQUIRED",
[](https://a2a-protocol.org/latest/specification/#__codelineno-13-9)      "message": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-13-10)        "role": "ROLE_AGENT",
[](https://a2a-protocol.org/latest/specification/#__codelineno-13-11)        "parts": [{"text": "I need more details. Where would you like to fly from and to?"}]
[](https://a2a-protocol.org/latest/specification/#__codelineno-13-12)      }
[](https://a2a-protocol.org/latest/specification/#__codelineno-13-13)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-13-14)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-13-15)}

```

**Follow-up Request:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-14-1)POST /message:send HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-14-2)Host: agent.example.com
[](https://a2a-protocol.org/latest/specification/#__codelineno-14-3)Content-Type: application/a2a+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-14-4)Authorization: Bearer token
[](https://a2a-protocol.org/latest/specification/#__codelineno-14-5)
[](https://a2a-protocol.org/latest/specification/#__codelineno-14-6){
[](https://a2a-protocol.org/latest/specification/#__codelineno-14-7)  "message": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-14-8)    "taskId": "task-uuid",
[](https://a2a-protocol.org/latest/specification/#__codelineno-14-9)    "role": "ROLE_USER",
[](https://a2a-protocol.org/latest/specification/#__codelineno-14-10)    "parts": [{"text": "From San Francisco to New York"}],
[](https://a2a-protocol.org/latest/specification/#__codelineno-14-11)    "messageId": "msg-2"
[](https://a2a-protocol.org/latest/specification/#__codelineno-14-12)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-14-13)}

```

### 6.4. Version Negotiation Error[¶](https://a2a-protocol.org/latest/specification/#64-version-negotiation-error "Permanent link")
**Scenario:** Client requests an unsupported protocol version.
**Request:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-15-1)POST /message:send HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-15-2)Host: agent.example.com
[](https://a2a-protocol.org/latest/specification/#__codelineno-15-3)Content-Type: application/a2a+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-15-4)Authorization: Bearer token
[](https://a2a-protocol.org/latest/specification/#__codelineno-15-5)A2A-Version: 0.5
[](https://a2a-protocol.org/latest/specification/#__codelineno-15-6)
[](https://a2a-protocol.org/latest/specification/#__codelineno-15-7){
[](https://a2a-protocol.org/latest/specification/#__codelineno-15-8)  "message": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-15-9)    "role": "ROLE_USER",
[](https://a2a-protocol.org/latest/specification/#__codelineno-15-10)    "parts": [{"text": "Hello"}],
[](https://a2a-protocol.org/latest/specification/#__codelineno-15-11)    "messageId": "msg-uuid"
[](https://a2a-protocol.org/latest/specification/#__codelineno-15-12)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-15-13)}

```

**Response:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-16-1)HTTP/1.1 400 Bad Request
[](https://a2a-protocol.org/latest/specification/#__codelineno-16-2)Content-Type: application/problem+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-16-3)
[](https://a2a-protocol.org/latest/specification/#__codelineno-16-4){
[](https://a2a-protocol.org/latest/specification/#__codelineno-16-5)  "type": "https://a2a-protocol.org/errors/version-not-supported",
[](https://a2a-protocol.org/latest/specification/#__codelineno-16-6)  "title": "Protocol Version Not Supported",
[](https://a2a-protocol.org/latest/specification/#__codelineno-16-7)  "status": 400,
[](https://a2a-protocol.org/latest/specification/#__codelineno-16-8)  "detail": "The requested A2A protocol version 0.5 is not supported by this agent",
[](https://a2a-protocol.org/latest/specification/#__codelineno-16-9)  "supportedVersions": ["0.3"]
[](https://a2a-protocol.org/latest/specification/#__codelineno-16-10)}

```

### 6.5. Task Listing and Management[¶](https://a2a-protocol.org/latest/specification/#65-task-listing-and-management "Permanent link")
**Scenario:** Client wants to see all tasks from a specific context or all tasks with a particular status.
#### Request: All tasks from a specific context[¶](https://a2a-protocol.org/latest/specification/#request-all-tasks-from-a-specific-context "Permanent link")
**Request:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-17-1)GET /tasks?contextId=c295ea44-7543-4f78-b524-7a38915ad6e4&pageSize=10&historyLength=3 HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-17-2)Host: agent.example.com
[](https://a2a-protocol.org/latest/specification/#__codelineno-17-3)Authorization: Bearer token

```

**Response:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-18-1)HTTP/1.1 200 OK
[](https://a2a-protocol.org/latest/specification/#__codelineno-18-2)Content-Type: application/a2a+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-18-3)
[](https://a2a-protocol.org/latest/specification/#__codelineno-18-4){
[](https://a2a-protocol.org/latest/specification/#__codelineno-18-5)  "tasks": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-18-6)    {
[](https://a2a-protocol.org/latest/specification/#__codelineno-18-7)      "id": "3f36680c-7f37-4a5f-945e-d78981fafd36",
[](https://a2a-protocol.org/latest/specification/#__codelineno-18-8)      "contextId": "c295ea44-7543-4f78-b524-7a38915ad6e4",
[](https://a2a-protocol.org/latest/specification/#__codelineno-18-9)      "status": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-18-10)        "state": "TASK_STATE_COMPLETED",
[](https://a2a-protocol.org/latest/specification/#__codelineno-18-11)        "timestamp": "2024-03-15T10:15:00Z"
[](https://a2a-protocol.org/latest/specification/#__codelineno-18-12)      }
[](https://a2a-protocol.org/latest/specification/#__codelineno-18-13)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-18-14)  ],
[](https://a2a-protocol.org/latest/specification/#__codelineno-18-15)  "totalSize": 5,
[](https://a2a-protocol.org/latest/specification/#__codelineno-18-16)  "pageSize": 10,
[](https://a2a-protocol.org/latest/specification/#__codelineno-18-17)  "nextPageToken": ""
[](https://a2a-protocol.org/latest/specification/#__codelineno-18-18)}

```

#### Request: All working tasks across all contexts[¶](https://a2a-protocol.org/latest/specification/#request-all-working-tasks-across-all-contexts "Permanent link")
**Request:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-19-1)GET /tasks?status=TASK_STATE_WORKING&pageSize=20 HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-19-2)Host: agent.example.com
[](https://a2a-protocol.org/latest/specification/#__codelineno-19-3)Authorization: Bearer token

```

**Response:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-1)HTTP/1.1 200 OK
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-2)Content-Type: application/a2a+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-3)
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-4){
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-5)  "tasks": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-6)    {
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-7)      "id": "789abc-def0-1234-5678-9abcdef01234",
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-8)      "contextId": "another-context-id",
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-9)      "status": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-10)        "state": "TASK_STATE_WORKING",
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-11)        "message": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-12)          "role": "ROLE_AGENT",
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-13)          "parts": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-14)            {
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-15)              "text": "Processing your document analysis..."
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-16)            }
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-17)          ],
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-18)          "messageId": "msg-status-update"
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-19)        },
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-20)        "timestamp": "2024-03-15T10:20:00Z"
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-21)      }
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-22)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-23)  ],
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-24)  "totalSize": 1,
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-25)  "pageSize": 20,
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-26)  "nextPageToken": ""
[](https://a2a-protocol.org/latest/specification/#__codelineno-20-27)}

```

#### Pagination Example[¶](https://a2a-protocol.org/latest/specification/#pagination-example "Permanent link")
**Request:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-21-1)GET /tasks?contextId=c295ea44-7543-4f78-b524-7a38915ad6e4&pageSize=10&pageToken=base64-encoded-cursor-token HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-21-2)Host: agent.example.com
[](https://a2a-protocol.org/latest/specification/#__codelineno-21-3)Authorization: Bearer token

```

**Response:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-22-1)HTTP/1.1 200 OK
[](https://a2a-protocol.org/latest/specification/#__codelineno-22-2)Content-Type: application/a2a+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-22-3)
[](https://a2a-protocol.org/latest/specification/#__codelineno-22-4){
[](https://a2a-protocol.org/latest/specification/#__codelineno-22-5)  "tasks": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-22-6)    /* ... additional tasks */
[](https://a2a-protocol.org/latest/specification/#__codelineno-22-7)  ],
[](https://a2a-protocol.org/latest/specification/#__codelineno-22-8)  "totalSize": 15,
[](https://a2a-protocol.org/latest/specification/#__codelineno-22-9)  "pageSize": 10,
[](https://a2a-protocol.org/latest/specification/#__codelineno-22-10)  "nextPageToken": "base64-encoded-next-cursor-token"
[](https://a2a-protocol.org/latest/specification/#__codelineno-22-11)}

```

#### Validation Error Example[¶](https://a2a-protocol.org/latest/specification/#validation-error-example "Permanent link")
**Request:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-23-1)GET /tasks?pageSize=150&historyLength=-5&status=TASK_STATE_RUNNING HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-23-2)Host: agent.example.com
[](https://a2a-protocol.org/latest/specification/#__codelineno-23-3)Authorization: Bearer token

```

**Response:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-1)HTTP/1.1 400 Bad Request
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-2)Content-Type: application/problem+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-3)
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-4){
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-5)  "status": 400,
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-6)  "detail": "Invalid parameters",
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-7)  "errors": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-8)    {
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-9)      "field": "pageSize",
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-10)      "message": "Must be between 1 and 100 inclusive, got 150"
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-11)    },
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-12)    {
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-13)      "field": "historyLength",
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-14)      "message": "Must be non-negative integer, got -5"
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-15)    },
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-16)    {
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-17)      "field": "status",
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-18)      "message": "Invalid status value 'running'. Must be one of: pending, working, completed, failed, canceled"
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-19)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-20)  ]
[](https://a2a-protocol.org/latest/specification/#__codelineno-24-21)}

```

### 6.6. Push Notification Setup and Usage[¶](https://a2a-protocol.org/latest/specification/#66-push-notification-setup-and-usage "Permanent link")
**Scenario:** Client requests a long-running report generation and wants to be notified via webhook when it's done.
**Initial Request with Push Notification Config:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-1)POST /message:send HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-2)Host: agent.example.com
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-3)Content-Type: application/a2a+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-4)Authorization: Bearer token
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-5)
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-6){
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-7)  "message": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-8)    "role": "ROLE_USER",
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-9)    "parts": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-10)      {
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-11)        "text": "Generate the Q1 sales report. This usually takes a while. Notify me when it's ready."
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-12)      }
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-13)    ],
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-14)    "messageId": "6dbc13b5-bd57-4c2b-b503-24e381b6c8d6"
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-15)  },
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-16)  "configuration": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-17)    "pushNotificationConfig": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-18)      "url": "https://client.example.com/webhook/a2a-notifications",
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-19)      "token": "secure-client-token-for-task-aaa",
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-20)      "authentication": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-21)        "schemes": ["Bearer"]
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-22)      }
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-23)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-24)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-25-25)}

```

**Response (Task Submitted):**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-26-1)HTTP/1.1 200 OK
[](https://a2a-protocol.org/latest/specification/#__codelineno-26-2)Content-Type: application/a2a+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-26-3)
[](https://a2a-protocol.org/latest/specification/#__codelineno-26-4){
[](https://a2a-protocol.org/latest/specification/#__codelineno-26-5)  "task": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-26-6)    "id": "43667960-d455-4453-b0cf-1bae4955270d",
[](https://a2a-protocol.org/latest/specification/#__codelineno-26-7)    "contextId": "c295ea44-7543-4f78-b524-7a38915ad6e4",
[](https://a2a-protocol.org/latest/specification/#__codelineno-26-8)    "status": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-26-9)      "state": "submitted",
[](https://a2a-protocol.org/latest/specification/#__codelineno-26-10)      "timestamp": "2024-03-15T11:00:00Z"
[](https://a2a-protocol.org/latest/specification/#__codelineno-26-11)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-26-12)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-26-13)}

```

**Later: Server POSTs Notification to Webhook:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-27-1)POST /webhook/a2a-notifications HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-27-2)Host: client.example.com
[](https://a2a-protocol.org/latest/specification/#__codelineno-27-3)Authorization: Bearer server-generated-jwt
[](https://a2a-protocol.org/latest/specification/#__codelineno-27-4)Content-Type: application/a2a+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-27-5)X-A2A-Notification-Token: secure-client-token-for-task-aaa
[](https://a2a-protocol.org/latest/specification/#__codelineno-27-6)
[](https://a2a-protocol.org/latest/specification/#__codelineno-27-7){
[](https://a2a-protocol.org/latest/specification/#__codelineno-27-8)  "statusUpdate": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-27-9)    "taskId": "43667960-d455-4453-b0cf-1bae4955270d",
[](https://a2a-protocol.org/latest/specification/#__codelineno-27-10)    "contextId": "c295ea44-7543-4f78-b524-7a38915ad6e4",
[](https://a2a-protocol.org/latest/specification/#__codelineno-27-11)    "status": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-27-12)      "state": "TASK_STATE_COMPLETED",
[](https://a2a-protocol.org/latest/specification/#__codelineno-27-13)      "timestamp": "2024-03-15T18:30:00Z"
[](https://a2a-protocol.org/latest/specification/#__codelineno-27-14)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-27-15)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-27-16)}

```

### 6.7. File Exchange (Upload and Download)[¶](https://a2a-protocol.org/latest/specification/#67-file-exchange-upload-and-download "Permanent link")
**Scenario:** Client sends an image for analysis, and the agent returns a modified image.
**Request with File Upload:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-1)POST /message:send HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-2)Host: agent.example.com
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-3)Content-Type: application/a2a+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-4)Authorization: Bearer token
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-5)
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-6){
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-7)  "message": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-8)    "role": "ROLE_USER",
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-9)    "parts": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-10)      {
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-11)        "text": "Analyze this image and highlight any faces."
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-12)      },
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-13)      {
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-14)        "raw": "iVBORw0KGgoAAAANSUhEUgAAAAUA..."
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-15)        "filename": "input_image.png",
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-16)        "mediaType": "image/png",
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-17)      }
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-18)    ],
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-19)    "messageId": "6dbc13b5-bd57-4c2b-b503-24e381b6c8d6"
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-20)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-28-21)}

```

**Response with File Reference:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-1)HTTP/1.1 200 OK
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-2)Content-Type: application/a2a+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-3)
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-4){
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-5)  "task": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-6)    "id": "43667960-d455-4453-b0cf-1bae4955270d",
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-7)    "contextId": "c295ea44-7543-4f78-b524-7a38915ad6e4",
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-8)    "status": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-9)      "state": "TASK_STATE_COMPLETED",
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-10)      "timestamp": "2024-03-15T12:05:00Z"
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-11)    },
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-12)    "artifacts": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-13)      {
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-14)        "artifactId": "9b6934dd-37e3-4eb1-8766-962efaab63a1",
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-15)        "name": "processed_image_with_faces.png",
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-16)        "parts": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-17)          {
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-18)            "url": "https://storage.example.com/processed/task-bbb/output.png?token=xyz",
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-19)            "filename": "output.png",
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-20)            "mediaType": "image/png"
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-21)          }
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-22)        ]
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-23)      }
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-24)    ]
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-25)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-29-26)}

```

### 6.8. Structured Data Exchange[¶](https://a2a-protocol.org/latest/specification/#68-structured-data-exchange "Permanent link")
**Scenario:** Client asks for a list of open support tickets in a specific JSON format.
**Request:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-1)POST /message:send HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-2)Host: agent.example.com
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-3)Content-Type: application/a2a+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-4)Authorization: Bearer token
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-5)
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-6){
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-7)  "message": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-8)    "role": "ROLE_USER",
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-9)    "parts": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-10)      {
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-11)        "text": "Show me a list of my open IT tickets",
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-12)        "metadata": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-13)          "mediaType": "application/json",
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-14)          "schema": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-15)            "type": "array",
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-16)            "items": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-17)              "type": "object",
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-18)              "properties": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-19)                "ticketNumber": { "type": "string" },
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-20)                "description": { "type": "string" }
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-21)              }
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-22)            }
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-23)          }
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-24)        }
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-25)      }
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-26)    ],
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-27)    "messageId": "85b26db5-ffbb-4278-a5da-a7b09dea1b47"
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-28)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-30-29)}

```

**Response with Structured Data:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-1)HTTP/1.1 200 OK
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-2)Content-Type: application/a2a+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-3)
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-4){
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-5)  "task": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-6)    "id": "d8c6243f-5f7a-4f6f-821d-957ce51e856c",
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-7)    "contextId": "c295ea44-7543-4f78-b524-7a38915ad6e4",
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-8)    "status": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-9)      "state": "TASK_STATE_COMPLETED",
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-10)      "timestamp": "2025-04-17T17:47:09.680794Z"
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-11)    },
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-12)    "artifacts": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-13)      {
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-14)        "artifactId": "c5e0382f-b57f-4da7-87d8-b85171fad17c",
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-15)        "parts": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-16)          {
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-17)            "text": "[{\"ticketNumber\":\"REQ12312\",\"description\":\"request for VPN access\"},{\"ticketNumber\":\"REQ23422\",\"description\":\"Add to DL - team-gcp-onboarding\"}]"
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-18)          }
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-19)        ]
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-20)      }
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-21)    ]
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-22)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-31-23)}

```

### 6.9. Fetching Authenticated Extended Agent Card[¶](https://a2a-protocol.org/latest/specification/#69-fetching-authenticated-extended-agent-card "Permanent link")
**Scenario:** A client discovers a public Agent Card indicating support for an authenticated extended card and wants to retrieve the full details.
**Step 1: Client fetches the public Agent Card:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-32-1)GET /.well-known/agent-card.json HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-32-2)Host: example.com

```

**Response includes:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-33-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-33-2)  "capabilities": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-33-3)    "extendedAgentCard": true
[](https://a2a-protocol.org/latest/specification/#__codelineno-33-4)  },
[](https://a2a-protocol.org/latest/specification/#__codelineno-33-5)  "securitySchemes": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-33-6)    "google": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-33-7)      "openIdConnectSecurityScheme": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-33-8)        "openIdConnectUrl": "https://accounts.google.com/.well-known/openid-configuration"
[](https://a2a-protocol.org/latest/specification/#__codelineno-33-9)      }
[](https://a2a-protocol.org/latest/specification/#__codelineno-33-10)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-33-11)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-33-12)}

```

### Step 2: Client obtains credentials (out-of-band OAuth 2.0 flow)[¶](https://a2a-protocol.org/latest/specification/#step-2-client-obtains-credentials-out-of-band-oauth-20-flow "Permanent link")
### Step 3: Client fetches authenticated extended Agent Card[¶](https://a2a-protocol.org/latest/specification/#step-3-client-fetches-authenticated-extended-agent-card "Permanent link")

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-34-1)GET /extendedAgentCard HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-34-2)Host: agent.example.com
[](https://a2a-protocol.org/latest/specification/#__codelineno-34-3)Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

```

**Response:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-35-1)HTTP/1.1 200 OK
[](https://a2a-protocol.org/latest/specification/#__codelineno-35-2)Content-Type: application/a2a+json
[](https://a2a-protocol.org/latest/specification/#__codelineno-35-3)
[](https://a2a-protocol.org/latest/specification/#__codelineno-35-4){
[](https://a2a-protocol.org/latest/specification/#__codelineno-35-5)  "name": "Extended Agent with Additional Skills",
[](https://a2a-protocol.org/latest/specification/#__codelineno-35-6)  "skills": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-35-7)    /* Extended skills available to authenticated users */
[](https://a2a-protocol.org/latest/specification/#__codelineno-35-8)  ]
[](https://a2a-protocol.org/latest/specification/#__codelineno-35-9)}

```

## 7. Authentication and Authorization[¶](https://a2a-protocol.org/latest/specification/#7-authentication-and-authorization "Permanent link")
A2A treats agents as standard enterprise applications, relying on established web security practices. Identity information is handled at the protocol layer, not within A2A semantics.
For a comprehensive guide on enterprise security aspects, see [Enterprise-Ready Features](https://a2a-protocol.org/latest/topics/enterprise-ready/).
### 7.1. Protocol Security[¶](https://a2a-protocol.org/latest/specification/#71-protocol-security "Permanent link")
Production deployments **MUST** use encrypted communication (HTTPS for HTTP-based bindings, TLS for gRPC). Implementations **SHOULD** use modern TLS configurations (TLS 1.3+ recommended) with strong cipher suites.
### 7.2. Server Identity Verification[¶](https://a2a-protocol.org/latest/specification/#72-server-identity-verification "Permanent link")
A2A Clients **SHOULD** verify the A2A Server's identity by validating its TLS certificate against trusted certificate authorities (CAs) during the TLS handshake.
### 7.3. Client Authentication Process[¶](https://a2a-protocol.org/latest/specification/#73-client-authentication-process "Permanent link")
  1. **Discovery of Requirements:** The client discovers the server's required authentication schemes via the `securitySchemes` field in the AgentCard.
  2. **Credential Acquisition (Out-of-Band):** The client obtains the necessary credentials through an out-of-band process specific to the required authentication scheme.
  3. **Credential Transmission:** The client includes these credentials in protocol-appropriate headers or metadata for every A2A request.


### 7.4. Server Authentication Responsibilities[¶](https://a2a-protocol.org/latest/specification/#74-server-authentication-responsibilities "Permanent link")
The A2A Server:
  * **MUST** authenticate every incoming request based on the provided credentials and its declared authentication requirements.
  * **SHOULD** use appropriate binding-specific error codes for authentication challenges or rejections.
  * **SHOULD** provide relevant authentication challenge information with error responses.


### 7.5. Server Authorization Responsibilities[¶](https://a2a-protocol.org/latest/specification/#75-server-authorization-responsibilities "Permanent link")
Once authenticated, the A2A Server authorizes requests based on the authenticated identity and its own policies. Authorization logic is implementation-specific and **MAY** consider:
  * Specific skills requested
  * Actions attempted within tasks
  * Data access policies
  * OAuth scopes (if applicable)


### 7.6. In-Task Authorization[¶](https://a2a-protocol.org/latest/specification/#76-in-task-authorization "Permanent link")
In the course of performing a task, an agent may require authorization to perform some action. Examples include:
  * An agent requiring an OAuth access token to call an API or another agent
  * An agent requiring human approval before a destructive action is taken


In the sections below, we refer to the object that represents the approved authorization as a credential.
Agents may have multiple means for retrieving this authorization, such as via directly sending messages to a human.
A2A provides the capability for agents to delegate the fulfillment of this authorization to the client via the `TASK_STATE_AUTH_REQUIRED` Task state. This provides agents a fallback path for requesting authorization by passing the responsibility to the client.
#### 7.6.1 In-Task Authorization Agent Responsibilities[¶](https://a2a-protocol.org/latest/specification/#761-in-task-authorization-agent-responsibilities "Permanent link")
To request that a client fulfills an authorization request, the agent:
  1. MUST use a Task to track the operation it is performing
  2. MUST transition the TaskState to `TASK_STATE_AUTH_REQUIRED`
  3. MUST include a TaskStatus message explaining the required authorization, unless the details of the authorization have been negotiated out-of-band or via an extension


Agents MUST arrange to receive credentials via an out-of-band means, unless an in-band mechanism has been negotiated out-of-band or via an extension.
If the credential is received out-of-band, the agent SHOULD maintain any active response streams with the client after setting the TaskState to `TASK_STATE_AUTH_REQUIRED`. The agent MAY immediately continue Task processing after receiving the credential, without a requirement that clients send a follow-up message.
Agents SHOULD support receiving messages directed to the Task while the Task remains in `TASK_STATE_AUTH_REQUIRED`. This enables clients to negotiate, correct, or reject an authorization request.
#### 7.6.2 In-Task Authorization Client Responsibilities[¶](https://a2a-protocol.org/latest/specification/#762-in-task-authorization-client-responsibilities "Permanent link")
Upon receiving a Task in `TASK_STATE_AUTH_REQUIRED`, a client is expected to take action in some way to resolve the agent's request for authorization.
A client may:
  * Send a response message to the Task to negotiate, correct, or reject the authorization request.
  * Contact another human, agent, or service to fulfill the authorization request
  * Directly fulfill the authorization request via an out-of-band or extension negotiated means


If the client is itself an A2A agent actively processing a Task, the client may further delegate the authorization request to its client by transitioning its own Task to `TASK_STATE_AUTH_REQUIRED`. The client SHOULD follow all [In-Task Authorization Agent Responsibilities](https://a2a-protocol.org/latest/specification/#761-in-task-authorization-agent-responsibilities). This enables forming a chain of Tasks in `TASK_STATE_AUTH_REQUIRED`.
Clients may not be aware of when the agent receives credentials out-of-band and subsequently continues Task processing. If a client does not have an active response stream open with the agent, the client risks missing Task updates. To avoid this, a client SHOULD perform one of the following:
  * Subscribe to a stream of events for the Task using the [Subscribe to Task](https://a2a-protocol.org/latest/specification/#316-subscribe-to-task) operation
  * Register a webhook to receive events, if supported by the agent, using the [Create Push Notification Config](https://a2a-protocol.org/latest/specification/#317-create-push-notification-config) operation
  * Begin polling the Task using the [Get Task](https://a2a-protocol.org/latest/specification/#313-get-task) operation


#### 7.6.3 In-Task Authorization Security Considerations[¶](https://a2a-protocol.org/latest/specification/#763-in-task-authorization-security-considerations "Permanent link")
Agents SHOULD receive credentials for in-task authorization requests out of band via a secure channel, such as HTTPS. This ensures that credentials are provided directly to the agent.
In-band credential exchange may be negotiated via out-of-band means or by using extensions. In-band credential exchange can allow credentials to be passed across chains of multiple A2A agents, exposing those credentials to each agent participating in the chain.
If using in-band credential exchange, we recommend adhering to the following security practices:
  * Credentials SHOULD be bound to the agent which originated the request, such that only this agent is able to use the credentials. This ensures that credentials propagating through a chain of A2A requests are only usable by the requesting agent.
  * Credentials containing sensitive information SHOULD be only readable by the agent which originated the request, such as by encrypting the credential.


## 8. Agent Discovery: The Agent Card[¶](https://a2a-protocol.org/latest/specification/#8-agent-discovery-the-agent-card "Permanent link")
### 8.1. Purpose[¶](https://a2a-protocol.org/latest/specification/#81-purpose "Permanent link")
A2A Servers **MUST** make an Agent Card available. The Agent Card describes the server's identity, capabilities, skills, and interaction requirements. Clients use this information for discovering suitable agents and configuring interactions.
For more on discovery strategies, see the [Agent Discovery guide](https://a2a-protocol.org/latest/topics/agent-discovery/).
### 8.2. Discovery Mechanisms[¶](https://a2a-protocol.org/latest/specification/#82-discovery-mechanisms "Permanent link")
Clients can find Agent Cards through:
  * **Well-Known URI:** Accessing `https://{server_domain}/.well-known/agent-card.json` (see [Section 8.6](https://a2a-protocol.org/latest/specification/#86-caching) for caching guidance)
  * **Registries/Catalogs:** Querying curated catalogs of agents
  * **Direct Configuration:** Pre-configured Agent Card URLs or content


### 8.3. Protocol Declaration Requirements[¶](https://a2a-protocol.org/latest/specification/#83-protocol-declaration-requirements "Permanent link")
The AgentCard **MUST** properly declare supported protocols:
#### 8.3.1. Supported Interfaces Declaration[¶](https://a2a-protocol.org/latest/specification/#831-supported-interfaces-declaration "Permanent link")
  * The `supportedInterfaces` field **SHOULD** declare all supported protocol combinations in preference order
  * The first entry in `supportedInterfaces` represents the preferred interface
  * Each interface **MUST** accurately declare its transport protocol and URL
  * URLs **MAY** be reused if multiple transports are available at the same endpoint


#### 8.3.2. Client Protocol Selection[¶](https://a2a-protocol.org/latest/specification/#832-client-protocol-selection "Permanent link")
Clients **MUST** follow these rules:
  1. Parse `supportedInterfaces` if present, and select the first supported transport
  2. Prefer earlier entries in the ordered list when multiple options are supported
  3. Use the correct URL for the selected transport


### 8.4. Agent Card Signing[¶](https://a2a-protocol.org/latest/specification/#84-agent-card-signing "Permanent link")
Agent Cards **MAY** be digitally signed using JSON Web Signature (JWS) as defined in [RFC 7515](https://tools.ietf.org/html/rfc7515) to ensure authenticity and integrity. Signatures allow clients to verify that an Agent Card has not been tampered with and originates from the claimed provider.
#### 8.4.1. Canonicalization Requirements[¶](https://a2a-protocol.org/latest/specification/#841-canonicalization-requirements "Permanent link")
Before signing, the Agent Card content **MUST** be canonicalized using the JSON Canonicalization Scheme (JCS) as defined in [RFC 8785](https://tools.ietf.org/html/rfc8785). This ensures consistent signature generation and verification across different JSON implementations.
**Canonicalization Rules:**
  1. **Field Presence and Default Value Handling** : Before canonicalization, the JSON representation **MUST** respect Protocol Buffer field presence semantics as defined in [Section 5.7](https://a2a-protocol.org/latest/specification/#57-field-presence-and-optionality). This ensures that the canonical form accurately reflects which fields were explicitly provided versus which were omitted, enabling signature verification when Agent Cards are reconstructed:
     * **Optional fields not explicitly set** : Fields marked with the `optional` keyword that were not explicitly set **MUST** be omitted from the JSON object
     * **Optional fields explicitly set to defaults** : Fields marked with `optional` that were explicitly set to a value (even if that value matches a default) **MUST** be included in the JSON object
     * **Required fields** : Fields marked with `REQUIRED` **MUST** always be present, even if the field value matches the default.
     * **Default values** : Fields with default values **MUST** be omitted unless the field is marked as `REQUIRED` or has the `optional` keyword.
  2. **RFC 8785 Compliance** : The Agent Card JSON **MUST** be canonicalized according to RFC 8785, which specifies:
     * Predictable ordering of object properties (lexicographic by key)
     * Consistent representation of numbers, strings, and other primitive values
     * Removal of insignificant whitespace
  3. **Signature Field Exclusion** : The `signatures` field itself **MUST** be excluded from the content being signed to avoid circular dependencies.


**Example of Default Value Removal:**
Original Agent Card fragment:

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-36-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-36-2)  "name": "Example Agent",
[](https://a2a-protocol.org/latest/specification/#__codelineno-36-3)  "description": "",
[](https://a2a-protocol.org/latest/specification/#__codelineno-36-4)  "capabilities": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-36-5)    "streaming": false,
[](https://a2a-protocol.org/latest/specification/#__codelineno-36-6)    "pushNotifications": false,
[](https://a2a-protocol.org/latest/specification/#__codelineno-36-7)    "extensions": []
[](https://a2a-protocol.org/latest/specification/#__codelineno-36-8)  },
[](https://a2a-protocol.org/latest/specification/#__codelineno-36-9)  "skills": []
[](https://a2a-protocol.org/latest/specification/#__codelineno-36-10)}

```

Applying the canonicalization rules:
  * `name`: "Example Agent" - REQUIRED field ? **include**
  * `description`: "" - REQUIRED field ? **include**
  * `capabilities`: object - REQUIRED field ? **include** (after processing children)
    * `streaming`: false - optional field, present in JSON (explicitly set) ? **include**
    * `pushNotifications`: false - optional field, present in JSON (explicitly set) ? **include**
    * `extensions`: [] - repeated field (not REQUIRED) with empty array ? **omit**
  * `skills`: [] - REQUIRED field ? **include**


After applying RFC 8785:

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-37-1){"capabilities":{"pushNotifications":false,"streaming":false},"description":"","name":"Example Agent","skills":[]}

```

#### 8.4.2. Signature Format[¶](https://a2a-protocol.org/latest/specification/#842-signature-format "Permanent link")
Signatures use the JSON Web Signature (JWS) format as defined in [RFC 7515](https://tools.ietf.org/html/rfc7515). The [`AgentCardSignature`](https://a2a-protocol.org/latest/specification/#447-agentcardsignature) object represents JWS components using three fields:
  * **`protected`**(required, string): Base64url-encoded JSON object containing the JWS Protected Header
  * **`signature`**(required, string): Base64url-encoded signature value
  * **`header`**(optional, object): JWS Unprotected Header as a JSON object (not base64url-encoded)


**JWS Protected Header Parameters:**
The protected header **MUST** include:
  * `alg`: Algorithm used for signing (e.g., "ES256", "RS256")
  * `typ`: **SHOULD** be set to "JOSE" for JWS
  * `kid`: Key ID for identifying the signing key


The protected header **MAY** include:
  * `jku`: URL to JSON Web Key Set (JWKS) containing the public key


**Signature Generation Process:**
  1. **Prepare the payload:**
     * Remove properties with default values from the Agent Card
     * Exclude the `signatures` field
     * Canonicalize the resulting JSON using RFC 8785 to produce the canonical payload
  2. **Create the protected header:**
     * Construct a JSON object with the required header parameters (`alg`, `typ`, `kid`) and any optional parameters (`jku`)
     * Serialize the header to JSON
     * Base64url-encode the serialized header to produce the `protected` field value
  3. **Compute the signature:**
     * Construct the JWS Signing Input: `ASCII(BASE64URL(UTF8(JWS Protected Header)) || '.' || BASE64URL(JWS Payload))`
     * Sign the JWS Signing Input using the algorithm specified in the `alg` header parameter and the private key
     * Base64url-encode the resulting signature bytes to produce the `signature` field value
  4. **Assemble the AgentCardSignature:**
     * Set `protected` to the base64url-encoded protected header from step 2
     * Set `signature` to the base64url-encoded signature value from step 3
     * Optionally set `header` to a JSON object containing any unprotected header parameters.


**Example:**
Given a canonical Agent Card payload and signing key, the signature generation produces:

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-38-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-38-2)  "protected": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpPU0UiLCJraWQiOiJrZXktMSIsImprdSI6Imh0dHBzOi8vZXhhbXBsZS5jb20vYWdlbnQvandrcy5qc29uIn0",
[](https://a2a-protocol.org/latest/specification/#__codelineno-38-3)  "signature": "QFdkNLNszlGj3z3u0YQGt_T9LixY3qtdQpZmsTdDHDe3fXV9y9-B3m2-XgCpzuhiLt8E0tV6HXoZKHv4GtHgKQ"
[](https://a2a-protocol.org/latest/specification/#__codelineno-38-4)}

```

Where the `protected` value decodes to:

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-39-1){"alg":"ES256","typ":"JOSE","kid":"key-1","jku":"https://example.com/agent/jwks.json"}

```

#### 8.4.3. Signature Verification[¶](https://a2a-protocol.org/latest/specification/#843-signature-verification "Permanent link")
Clients verifying Agent Card signatures **MUST** :
  1. Extract the signature from the `signatures` array
  2. Retrieve the public key using the `kid` and `jku` (or from a trusted key store)
  3. Remove properties with default values from the received Agent Card
  4. Exclude the `signatures` field
  5. Canonicalize the resulting JSON using RFC 8785
  6. Verify the signature against the canonicalized payload


**Security Considerations:**
  * Clients **SHOULD** verify at least one signature before trusting an Agent Card
  * Public keys **SHOULD** be retrieved over secure channels (HTTPS)
  * Clients **MAY** maintain a trusted key store for known agent providers
  * Expired or revoked keys **MUST NOT** be used for verification
  * Multiple signatures **MAY** be present to support key rotation


### 8.5. Sample Agent Card[¶](https://a2a-protocol.org/latest/specification/#85-sample-agent-card "Permanent link")

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-2)  "name": "GeoSpatial Route Planner Agent",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-3)  "description": "Provides advanced route planning, traffic analysis, and custom map generation services. This agent can calculate optimal routes, estimate travel times considering real-time traffic, and create personalized maps with points of interest.",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-4)  "supportedInterfaces": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-5)    {"url": "https://georoute-agent.example.com/a2a/v1", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"},
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-6)    {"url": "https://georoute-agent.example.com/a2a/grpc", "protocolBinding": "GRPC", "protocolVersion": "1.0"},
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-7)    {"url": "https://georoute-agent.example.com/a2a/json", "protocolBinding": "HTTP+JSON", "protocolVersion": "1.0"}
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-8)  ],
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-9)  "provider": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-10)    "organization": "Example Geo Services Inc.",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-11)    "url": "https://www.examplegeoservices.com"
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-12)  },
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-13)  "iconUrl": "https://georoute-agent.example.com/icon.png",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-14)  "version": "1.2.0",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-15)  "documentationUrl": "https://docs.examplegeoservices.com/georoute-agent/api",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-16)  "capabilities": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-17)    "streaming": true,
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-18)    "pushNotifications": true,
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-19)    "stateTransitionHistory": false,
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-20)    "extendedAgentCard": true
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-21)  },
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-22)  "securitySchemes": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-23)    "google": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-24)      "openIdConnectSecurityScheme": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-25)        "openIdConnectUrl": "https://accounts.google.com/.well-known/openid-configuration"
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-26)      }
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-27)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-28)  },
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-29)  "security": [{ "google": ["openid", "profile", "email"] }],
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-30)  "defaultInputModes": ["application/json", "text/plain"],
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-31)  "defaultOutputModes": ["application/json", "image/png"],
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-32)  "skills": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-33)    {
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-34)      "id": "route-optimizer-traffic",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-35)      "name": "Traffic-Aware Route Optimizer",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-36)      "description": "Calculates the optimal driving route between two or more locations, taking into account real-time traffic conditions, road closures, and user preferences (e.g., avoid tolls, prefer highways).",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-37)      "tags": ["maps", "routing", "navigation", "directions", "traffic"],
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-38)      "examples": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-39)        "Plan a route from '1600 Amphitheatre Parkway, Mountain View, CA' to 'San Francisco International Airport' avoiding tolls.",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-40)        "{\"origin\": {\"lat\": 37.422, \"lng\": -122.084}, \"destination\": {\"lat\": 37.7749, \"lng\": -122.4194}, \"preferences\": [\"avoid_ferries\"]}"
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-41)      ],
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-42)      "inputModes": ["application/json", "text/plain"],
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-43)      "outputModes": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-44)        "application/json",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-45)        "application/vnd.geo+json",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-46)        "text/html"
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-47)      ]
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-48)    },
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-49)    {
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-50)      "id": "custom-map-generator",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-51)      "name": "Personalized Map Generator",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-52)      "description": "Creates custom map images or interactive map views based on user-defined points of interest, routes, and style preferences. Can overlay data layers.",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-53)      "tags": ["maps", "customization", "visualization", "cartography"],
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-54)      "examples": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-55)        "Generate a map of my upcoming road trip with all planned stops highlighted.",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-56)        "Show me a map visualizing all coffee shops within a 1-mile radius of my current location."
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-57)      ],
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-58)      "inputModes": ["application/json"],
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-59)      "outputModes": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-60)        "image/png",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-61)        "image/jpeg",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-62)        "application/json",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-63)        "text/html"
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-64)      ]
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-65)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-66)  ],
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-67)  "signatures": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-68)    {
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-69)      "protected": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpPU0UiLCJraWQiOiJrZXktMSIsImprdSI6Imh0dHBzOi8vZXhhbXBsZS5jb20vYWdlbnQvandrcy5qc29uIn0",
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-70)      "signature": "QFdkNLNszlGj3z3u0YQGt_T9LixY3qtdQpZmsTdDHDe3fXV9y9-B3m2-XgCpzuhiLt8E0tV6HXoZKHv4GtHgKQ"
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-71)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-72)  ]
[](https://a2a-protocol.org/latest/specification/#__codelineno-40-73)}

```

### 8.6. Caching[¶](https://a2a-protocol.org/latest/specification/#86-caching "Permanent link")
Agent Card content changes infrequently relative to the frequency at which clients may fetch it. Servers and clients **SHOULD** use standard HTTP caching mechanisms to reduce unnecessary network overhead.
#### 8.6.1. Server Requirements[¶](https://a2a-protocol.org/latest/specification/#861-server-requirements "Permanent link")
  * Agent Card HTTP endpoints **SHOULD** include a `Cache-Control` response header with a `max-age` directive appropriate for the agent's expected update frequency
  * Agent Card HTTP endpoints **SHOULD** include an `ETag` response header derived from the Agent Card's `version` field or a hash of the card content
  * Agent Card HTTP endpoints **MAY** include a `Last-Modified` response header


#### 8.6.2. Client Requirements[¶](https://a2a-protocol.org/latest/specification/#862-client-requirements "Permanent link")
  * Clients **SHOULD** honor HTTP caching semantics as defined in [RFC 9111](https://www.rfc-editor.org/rfc/rfc9111) when fetching Agent Cards
  * When a cached Agent Card has expired, clients **SHOULD** use conditional requests (`If-None-Match` with the stored `ETag`, or `If-Modified-Since`) to avoid re-downloading unchanged cards
  * When the server does not include caching headers, clients **MAY** apply an implementation-specific default cache duration


## 9. JSON-RPC Protocol Binding[¶](https://a2a-protocol.org/latest/specification/#9-json-rpc-protocol-binding "Permanent link")
The JSON-RPC protocol binding provides a simple, HTTP-based interface using JSON-RPC 2.0 for method calls and Server-Sent Events for streaming.
### 9.1. Protocol Requirements[¶](https://a2a-protocol.org/latest/specification/#91-protocol-requirements "Permanent link")
  * **Protocol:** JSON-RPC 2.0 over HTTP(S)
  * **Content-Type:** `application/json` for requests and responses
  * **Method Naming:** PascalCase method names matching gRPC conventions (e.g., `SendMessage`, `GetTask`)
  * **Streaming:** Server-Sent Events (`text/event-stream`)


### 9.2. Service Parameter Transmission[¶](https://a2a-protocol.org/latest/specification/#92-service-parameter-transmission "Permanent link")
A2A service parameters defined in [Section 3.2.6](https://a2a-protocol.org/latest/specification/#326-service-parameters) **MUST** be transmitted using standard HTTP request headers, as JSON-RPC 2.0 operates over HTTP(S).
**Service Parameter Requirements:**
  * Service parameter names **MUST** be transmitted as HTTP header fields
  * Service parameter keys are case-insensitive per HTTP specification (RFC 7230)
  * Multiple values for the same service parameter (e.g., `A2A-Extensions`) **SHOULD** be comma-separated in a single header field


**Example Request with A2A Service Parameters:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-41-1)POST /rpc HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-41-2)Host: agent.example.com
[](https://a2a-protocol.org/latest/specification/#__codelineno-41-3)Content-Type: application/json
[](https://a2a-protocol.org/latest/specification/#__codelineno-41-4)Authorization: Bearer token
[](https://a2a-protocol.org/latest/specification/#__codelineno-41-5)A2A-Version: 0.3
[](https://a2a-protocol.org/latest/specification/#__codelineno-41-6)A2A-Extensions: https://example.com/extensions/geolocation/v1,https://standards.org/extensions/citations/v1
[](https://a2a-protocol.org/latest/specification/#__codelineno-41-7)
[](https://a2a-protocol.org/latest/specification/#__codelineno-41-8){
[](https://a2a-protocol.org/latest/specification/#__codelineno-41-9)  "jsonrpc": "2.0",
[](https://a2a-protocol.org/latest/specification/#__codelineno-41-10)  "id": 1,
[](https://a2a-protocol.org/latest/specification/#__codelineno-41-11)  "method": "SendMessage",
[](https://a2a-protocol.org/latest/specification/#__codelineno-41-12)  "params": { /* SendMessageRequest */ }
[](https://a2a-protocol.org/latest/specification/#__codelineno-41-13)}

```

### 9.3. Base Request Structure[¶](https://a2a-protocol.org/latest/specification/#93-base-request-structure "Permanent link")
All JSON-RPC requests **MUST** follow the standard JSON-RPC 2.0 format:

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-42-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-42-2)  "jsonrpc": "2.0",
[](https://a2a-protocol.org/latest/specification/#__codelineno-42-3)  "id": "unique-request-id",
[](https://a2a-protocol.org/latest/specification/#__codelineno-42-4)  "method": "category/action",
[](https://a2a-protocol.org/latest/specification/#__codelineno-42-5)  "params": { /* method-specific parameters */ }
[](https://a2a-protocol.org/latest/specification/#__codelineno-42-6)}

```

### 9.4. Core Methods[¶](https://a2a-protocol.org/latest/specification/#94-core-methods "Permanent link")
#### 9.4.1. `SendMessage`[¶](https://a2a-protocol.org/latest/specification/#941-sendmessage "Permanent link")
Sends a message to initiate or continue a task.
**Request:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-43-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-43-2)  "jsonrpc": "2.0",
[](https://a2a-protocol.org/latest/specification/#__codelineno-43-3)  "id": 1,
[](https://a2a-protocol.org/latest/specification/#__codelineno-43-4)  "method": "SendMessage",
[](https://a2a-protocol.org/latest/specification/#__codelineno-43-5)  "params": { /* SendMessageRequest object */ }
[](https://a2a-protocol.org/latest/specification/#__codelineno-43-6)}

```

**Referenced Objects:** [`SendMessageRequest`](https://a2a-protocol.org/latest/specification/#321-sendmessagerequest), [`Message`](https://a2a-protocol.org/latest/specification/#414-message)
**Response:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-44-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-44-2)  "jsonrpc": "2.0",
[](https://a2a-protocol.org/latest/specification/#__codelineno-44-3)  "id": 1,
[](https://a2a-protocol.org/latest/specification/#__codelineno-44-4)  "result": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-44-5)    /* SendMessageResponse object, contains one of:
[](https://a2a-protocol.org/latest/specification/#__codelineno-44-6)     * "task": { Task object }
[](https://a2a-protocol.org/latest/specification/#__codelineno-44-7)     * "message": { Message object }
[](https://a2a-protocol.org/latest/specification/#__codelineno-44-8)    */
[](https://a2a-protocol.org/latest/specification/#__codelineno-44-9)  }

```

**Referenced Objects:** [`Task`](https://a2a-protocol.org/latest/specification/#411-task), [`Message`](https://a2a-protocol.org/latest/specification/#414-message)
#### 9.4.2. `SendStreamingMessage`[¶](https://a2a-protocol.org/latest/specification/#942-sendstreamingmessage "Permanent link")
Sends a message and subscribes to real-time updates via Server-Sent Events.
**Request:** Same as `SendMessage`
**Response:** HTTP 200 with `Content-Type: text/event-stream`

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-45-1)data: {"jsonrpc": "2.0", "id": 1, "result": { /* StreamResponse object */ }}
[](https://a2a-protocol.org/latest/specification/#__codelineno-45-2)
[](https://a2a-protocol.org/latest/specification/#__codelineno-45-3)data: {"jsonrpc": "2.0", "id": 1, "result": { /* StreamResponse object */ }}

```

**Referenced Objects:** [`StreamResponse`](https://a2a-protocol.org/latest/specification/#323-stream-response)
#### 9.4.3. `GetTask`[¶](https://a2a-protocol.org/latest/specification/#943-gettask "Permanent link")
Retrieves the current state of a task.
**Request:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-46-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-46-2)  "jsonrpc": "2.0",
[](https://a2a-protocol.org/latest/specification/#__codelineno-46-3)  "id": 2,
[](https://a2a-protocol.org/latest/specification/#__codelineno-46-4)  "method": "GetTask",
[](https://a2a-protocol.org/latest/specification/#__codelineno-46-5)  "params": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-46-6)    "id": "task-uuid",
[](https://a2a-protocol.org/latest/specification/#__codelineno-46-7)    "historyLength": 10
[](https://a2a-protocol.org/latest/specification/#__codelineno-46-8)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-46-9)}

```

#### 9.4.4. `ListTasks`[¶](https://a2a-protocol.org/latest/specification/#944-listtasks "Permanent link")
Lists tasks with optional filtering and pagination.
**Request:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-47-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-47-2)  "jsonrpc": "2.0",
[](https://a2a-protocol.org/latest/specification/#__codelineno-47-3)  "id": 3,
[](https://a2a-protocol.org/latest/specification/#__codelineno-47-4)  "method": "ListTasks",
[](https://a2a-protocol.org/latest/specification/#__codelineno-47-5)  "params": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-47-6)    "contextId": "context-uuid",
[](https://a2a-protocol.org/latest/specification/#__codelineno-47-7)    "status": "TASK_STATE_WORKING",
[](https://a2a-protocol.org/latest/specification/#__codelineno-47-8)    "pageSize": 50,
[](https://a2a-protocol.org/latest/specification/#__codelineno-47-9)    "pageToken": "cursor-token"
[](https://a2a-protocol.org/latest/specification/#__codelineno-47-10)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-47-11)}

```

#### 9.4.5. `CancelTask`[¶](https://a2a-protocol.org/latest/specification/#945-canceltask "Permanent link")
Cancels an ongoing task.
**Request:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-48-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-48-2)  "jsonrpc": "2.0",
[](https://a2a-protocol.org/latest/specification/#__codelineno-48-3)  "id": 4,
[](https://a2a-protocol.org/latest/specification/#__codelineno-48-4)  "method": "CancelTask",
[](https://a2a-protocol.org/latest/specification/#__codelineno-48-5)  "params": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-48-6)    "id": "task-uuid"
[](https://a2a-protocol.org/latest/specification/#__codelineno-48-7)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-48-8)}

```

#### 9.4.6. `SubscribeToTask`[¶](https://a2a-protocol.org/latest/specification/#946-subscribetotask "Permanent link")
Subscribes to a task stream for receiving updates on a task that is not in a terminal state.
**Request:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-49-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-49-2)  "jsonrpc": "2.0",
[](https://a2a-protocol.org/latest/specification/#__codelineno-49-3)  "id": 5,
[](https://a2a-protocol.org/latest/specification/#__codelineno-49-4)  "method": "SubscribeToTask",
[](https://a2a-protocol.org/latest/specification/#__codelineno-49-5)  "params": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-49-6)    "id": "task-uuid"
[](https://a2a-protocol.org/latest/specification/#__codelineno-49-7)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-49-8)}

```

**Response:** SSE stream (same format as `SendStreamingMessage`)
**Error:** Returns `UnsupportedOperationError` if the task is in a terminal state (`completed`, `failed`, `canceled`, or `rejected`).
#### 9.4.7. Push Notification Configuration Methods[¶](https://a2a-protocol.org/latest/specification/#947-push-notification-configuration-methods "Permanent link")
  * `CreateTaskPushNotificationConfig` - Create push notification configuration
  * `GetTaskPushNotificationConfig` - Get push notification configuration
  * `ListTaskPushNotificationConfigs` - List push notification configurations
  * `DeleteTaskPushNotificationConfig` - Delete push notification configuration


#### 9.4.8. `GetExtendedAgentCard`[¶](https://a2a-protocol.org/latest/specification/#948-getextendedagentcard "Permanent link")
Retrieves an extended Agent Card.
**Request:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-50-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-50-2)  "jsonrpc": "2.0",
[](https://a2a-protocol.org/latest/specification/#__codelineno-50-3)  "id": 6,
[](https://a2a-protocol.org/latest/specification/#__codelineno-50-4)  "method": "GetExtendedAgentCard"
[](https://a2a-protocol.org/latest/specification/#__codelineno-50-5)}

```

### 9.5. Error Handling[¶](https://a2a-protocol.org/latest/specification/#95-error-handling "Permanent link")
JSON-RPC error responses use the standard [JSON-RPC 2.0 error object](https://www.jsonrpc.org/specification#error_object) structure, which maps to the generic A2A error model defined in [Section 3.3.2](https://a2a-protocol.org/latest/specification/#332-error-handling) as follows:
  * **Error Code** : Mapped to `error.code` (numeric JSON-RPC error code)
  * **Error Message** : Mapped to `error.message` (human-readable string)
  * **Error Details** : Mapped to `error.data` (array containing `google.protobuf.Any` messages, using ProtoJSON representation)


**Standard JSON-RPC Error Codes:**  
| JSON-RPC Error Code  | Error Name  | Standard Message  | Description  |  
| --- | --- | --- | --- |  
| `-32700`  | `JSONParseError`  | "Invalid JSON payload"  | The server received invalid JSON  |  
| `-32600`  | `InvalidRequestError`  | "Request payload validation error"  | The JSON sent is not a valid Request object  |  
| `-32601`  | `MethodNotFoundError`  | "Method not found"  | The requested method does not exist or is not available  |  
| `-32602`  | `InvalidParamsError`  | "Invalid parameters"  | The method parameters are invalid  |  
| `-32603`  | `InternalError`  | "Internal error"  | An internal error occurred on the server  |  
**A2A-Specific Error Codes:**
A2A-specific errors use codes in the range `-32001` to `-32099`. For the complete mapping of A2A error types to JSON-RPC error codes, see [Section 5.4 (Error Code Mappings)](https://a2a-protocol.org/latest/specification/#54-error-code-mappings).
**A2A Error Representation:**
For A2A-specific errors, implementations **MUST** include a `google.rpc.ErrorInfo` message in the `data` array with:
  * `@type`: Set to `"type.googleapis.com/google.rpc.ErrorInfo"`
  * `reason`: The A2A error type in UPPER_SNAKE_CASE without the "Error" suffix (e.g., `TASK_NOT_FOUND`)
  * `domain`: Set to `"a2a-protocol.org"`
  * `metadata`: Optional map of additional error context


Additional error context **MAY** be included in the `data` array.
**Error Response Structure:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-51-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-51-2)  "jsonrpc": "2.0",
[](https://a2a-protocol.org/latest/specification/#__codelineno-51-3)  "id": 1,
[](https://a2a-protocol.org/latest/specification/#__codelineno-51-4)  "error": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-51-5)    "code": -32601,
[](https://a2a-protocol.org/latest/specification/#__codelineno-51-6)    "message": "Method not found",
[](https://a2a-protocol.org/latest/specification/#__codelineno-51-7)    "data": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-51-8)      "method": "invalid/method"
[](https://a2a-protocol.org/latest/specification/#__codelineno-51-9)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-51-10)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-51-11)}

```

**Example A2A-Specific Error Response:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-52-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-52-2)  "jsonrpc": "2.0",
[](https://a2a-protocol.org/latest/specification/#__codelineno-52-3)  "id": 2,
[](https://a2a-protocol.org/latest/specification/#__codelineno-52-4)  "error": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-52-5)    "code": -32001,
[](https://a2a-protocol.org/latest/specification/#__codelineno-52-6)    "message": "Task not found",
[](https://a2a-protocol.org/latest/specification/#__codelineno-52-7)    "data": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-52-8)      {
[](https://a2a-protocol.org/latest/specification/#__codelineno-52-9)        "@type": "type.googleapis.com/google.rpc.ErrorInfo",
[](https://a2a-protocol.org/latest/specification/#__codelineno-52-10)        "reason": "TASK_NOT_FOUND",
[](https://a2a-protocol.org/latest/specification/#__codelineno-52-11)        "domain": "a2a-protocol.org",
[](https://a2a-protocol.org/latest/specification/#__codelineno-52-12)        "metadata": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-52-13)          "taskId": "nonexistent-task-id",
[](https://a2a-protocol.org/latest/specification/#__codelineno-52-14)          "timestamp": "2025-11-09T10:30:00.000Z"
[](https://a2a-protocol.org/latest/specification/#__codelineno-52-15)        }
[](https://a2a-protocol.org/latest/specification/#__codelineno-52-16)      }
[](https://a2a-protocol.org/latest/specification/#__codelineno-52-17)    ]
[](https://a2a-protocol.org/latest/specification/#__codelineno-52-18)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-52-19)}

```

## 10. gRPC Protocol Binding[¶](https://a2a-protocol.org/latest/specification/#10-grpc-protocol-binding "Permanent link")
The gRPC Protocol Binding provides a high-performance, strongly-typed interface using Protocol Buffers over HTTP/2. The gRPC Protocol Binding leverages the [API guidelines](https://google.aip.dev/general) to simplify gRPC to HTTP mapping.
### 10.1. Protocol Requirements[¶](https://a2a-protocol.org/latest/specification/#101-protocol-requirements "Permanent link")
  * **Protocol:** gRPC over HTTP/2 with TLS
  * **Definition:** Use the normative Protocol Buffers definition in `specification/a2a.proto`
  * **Serialization:** Protocol Buffers version 3
  * **Service:** Implement the `A2AService` gRPC service


### 10.2. Service Parameter Transmission[¶](https://a2a-protocol.org/latest/specification/#102-service-parameter-transmission "Permanent link")
A2A service parameters defined in [Section 3.2.6](https://a2a-protocol.org/latest/specification/#326-service-parameters) **MUST** be transmitted using gRPC metadata (headers).
**Service Parameter Requirements:**
  * Service parameter names **MUST** be transmitted as gRPC metadata keys
  * Metadata keys are case-insensitive and automatically converted to lowercase by gRPC
  * Multiple values for the same service parameter (e.g., `A2A-Extensions`) **SHOULD** be comma-separated in a single metadata entry


**Example gRPC Request with A2A Service Parameters:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-53-1)// Go example using gRPC metadata
[](https://a2a-protocol.org/latest/specification/#__codelineno-53-2)md := metadata.Pairs(
[](https://a2a-protocol.org/latest/specification/#__codelineno-53-3)    "authorization", "Bearer token",
[](https://a2a-protocol.org/latest/specification/#__codelineno-53-4)    "a2a-version", "0.3",
[](https://a2a-protocol.org/latest/specification/#__codelineno-53-5)    "a2a-extensions", "https://example.com/extensions/geolocation/v1,https://standards.org/extensions/citations/v1",
[](https://a2a-protocol.org/latest/specification/#__codelineno-53-6))
[](https://a2a-protocol.org/latest/specification/#__codelineno-53-7)ctx := metadata.NewOutgoingContext(context.Background(), md)
[](https://a2a-protocol.org/latest/specification/#__codelineno-53-8)
[](https://a2a-protocol.org/latest/specification/#__codelineno-53-9)// Make the RPC call with the context containing metadata
[](https://a2a-protocol.org/latest/specification/#__codelineno-53-10)response, err := client.SendMessage(ctx, request)

```

**Metadata Handling:**
  * Implementations **MUST** extract A2A service parameters from gRPC metadata for processing
  * Servers **SHOULD** validate required service parameters (e.g., `A2A-Version`) from metadata
  * Service parameter keys in metadata are normalized to lowercase per gRPC conventions


### 10.3. Service Definition[¶](https://a2a-protocol.org/latest/specification/#103-service-definition "Permanent link")  
| Method  | Request  | Response  | Description  |  
| --- | --- | --- | --- |  
| `SendMessage`  | [`SendMessageRequest`](https://a2a-protocol.org/latest/specification/#sendmessagerequest)  | [`SendMessageResponse`](https://a2a-protocol.org/latest/specification/#sendmessageresponse)  | Sends a message to an agent.  |  
| `SendStreamingMessage`  | [`SendMessageRequest`](https://a2a-protocol.org/latest/specification/#sendmessagerequest)  | stream [`StreamResponse`](https://a2a-protocol.org/latest/specification/#streamresponse)  | Sends a streaming message to an agent, allowing for real-time interaction and status updates. Streaming version of `SendMessage`  |  
| `GetTask`  | [`GetTaskRequest`](https://a2a-protocol.org/latest/specification/#gettaskrequest)  | [`Task`](https://a2a-protocol.org/latest/specification/#task)  | Gets the latest state of a task.  |  
| `ListTasks`  | [`ListTasksRequest`](https://a2a-protocol.org/latest/specification/#listtasksrequest)  | [`ListTasksResponse`](https://a2a-protocol.org/latest/specification/#listtasksresponse)  | Lists tasks that match the specified filter.  |  
| `CancelTask`  | [`CancelTaskRequest`](https://a2a-protocol.org/latest/specification/#canceltaskrequest)  | [`Task`](https://a2a-protocol.org/latest/specification/#task)  | Cancels a task in progress.  |  
| `SubscribeToTask`  | [`SubscribeToTaskRequest`](https://a2a-protocol.org/latest/specification/#subscribetotaskrequest)  | stream [`StreamResponse`](https://a2a-protocol.org/latest/specification/#streamresponse)  | Subscribes to task updates for tasks not in a terminal state. Returns `UnsupportedOperationError` if the task is already in a terminal state (completed, failed, canceled, rejected).  |  
| `CreateTaskPushNotificationConfig`  | [`TaskPushNotificationConfig`](https://a2a-protocol.org/latest/specification/#taskpushnotificationconfig)  | [`TaskPushNotificationConfig`](https://a2a-protocol.org/latest/specification/#taskpushnotificationconfig)  | Creates a push notification config for a task.  |  
| `GetTaskPushNotificationConfig`  | [`GetTaskPushNotificationConfigRequest`](https://a2a-protocol.org/latest/specification/#gettaskpushnotificationconfigrequest)  | [`TaskPushNotificationConfig`](https://a2a-protocol.org/latest/specification/#taskpushnotificationconfig)  | Gets a push notification config for a task.  |  
| `ListTaskPushNotificationConfigs`  | [`ListTaskPushNotificationConfigsRequest`](https://a2a-protocol.org/latest/specification/#listtaskpushnotificationconfigsrequest)  | [`ListTaskPushNotificationConfigsResponse`](https://a2a-protocol.org/latest/specification/#listtaskpushnotificationconfigsresponse)  | Get a list of push notifications configured for a task.  |  
| `GetExtendedAgentCard`  | [`GetExtendedAgentCardRequest`](https://a2a-protocol.org/latest/specification/#getextendedagentcardrequest)  | [`AgentCard`](https://a2a-protocol.org/latest/specification/#agentcard)  | Gets the extended agent card for the authenticated agent.  |  
| `DeleteTaskPushNotificationConfig`  | [`DeleteTaskPushNotificationConfigRequest`](https://a2a-protocol.org/latest/specification/#deletetaskpushnotificationconfigrequest)  | `empty`  | Deletes a push notification config for a task.  |  
### 10.4. Core Methods[¶](https://a2a-protocol.org/latest/specification/#104-core-methods "Permanent link")
#### 10.4.1. SendMessage[¶](https://a2a-protocol.org/latest/specification/#1041-sendmessage "Permanent link")
Sends a message to an agent.
**Request:**
Represents a request for the `SendMessage` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Optional. Tenant ID, provided as a path parameter.  |  
| `message`  | [`Message`](https://a2a-protocol.org/latest/specification/#message)  | Yes  | The message to send to the agent.  |  
| `configuration`  | [`SendMessageConfiguration`](https://a2a-protocol.org/latest/specification/#sendmessageconfiguration)  | No  | Configuration for the send request.  |  
| `metadata`  | `object`  | No  | A flexible key-value map for passing additional context or parameters.  |  
**Response:**
Represents the response for the `SendMessage` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `task`  | [`Task`](https://a2a-protocol.org/latest/specification/#task)  | Optional (OneOf)  | The task created or updated by the message.  |  
| `message`  | [`Message`](https://a2a-protocol.org/latest/specification/#message)  | Optional (OneOf)  | A message from the agent.  |  
**Note:** A `SendMessageResponse` MUST contain exactly one of the following: `task`, `message`
#### 10.4.2. SendStreamingMessage[¶](https://a2a-protocol.org/latest/specification/#1042-sendstreamingmessage "Permanent link")
Sends a message with streaming updates.
**Request:**
Represents a request for the `SendMessage` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Optional. Tenant ID, provided as a path parameter.  |  
| `message`  | [`Message`](https://a2a-protocol.org/latest/specification/#message)  | Yes  | The message to send to the agent.  |  
| `configuration`  | [`SendMessageConfiguration`](https://a2a-protocol.org/latest/specification/#sendmessageconfiguration)  | No  | Configuration for the send request.  |  
| `metadata`  | `object`  | No  | A flexible key-value map for passing additional context or parameters.  |  
**Response:** Server streaming [`StreamResponse`](https://a2a-protocol.org/latest/specification/#stream-response) objects.
#### 10.4.3. GetTask[¶](https://a2a-protocol.org/latest/specification/#1043-gettask "Permanent link")
Retrieves task status.
**Request:**
Represents a request for the `GetTask` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Optional. Tenant ID, provided as a path parameter.  |  
| `id`  | `string`  | Yes  | The resource ID of the task to retrieve.  |  
| `historyLength`  | `integer`  | No  | The maximum number of most recent messages from the task's history to retrieve. An unset value means the client does not impose any limit. A value of zero is a request to not include any messages. The server MUST NOT return more messages than the provided value, but MAY apply a lower limit.  |  
**Response:** See [`Task`](https://a2a-protocol.org/latest/specification/#411-task) object definition.
#### 10.4.4. ListTasks[¶](https://a2a-protocol.org/latest/specification/#1044-listtasks "Permanent link")
Lists tasks with filtering.
**Request:**
Parameters for listing tasks with optional filtering criteria.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Tenant ID, provided as a path parameter.  |  
| `contextId`  | `string`  | No  | Filter tasks by context ID to get tasks from a specific conversation or session.  |  
| `status`  | [`TaskState`](https://a2a-protocol.org/latest/specification/#taskstate)  | No  | Filter tasks by their current status state.  |  
| `pageSize`  | `integer`  | No  | The maximum number of tasks to return. The service may return fewer than this value. If unspecified, at most 50 tasks will be returned. The minimum value is 1. The maximum value is 100.  |  
| `pageToken`  | `string`  | No  | A page token, received from a previous `ListTasks` call. `ListTasksResponse.next_page_token`. Provide this to retrieve the subsequent page.  |  
| `historyLength`  | `integer`  | No  | The maximum number of messages to include in each task's history.  |  
| `statusTimestampAfter`  | `timestamp`  | No  | Filter tasks which have a status updated after the provided timestamp in ISO 8601 format (e.g., "2023-10-27T10:00:00Z"). Only tasks with a status timestamp time greater than or equal to this value will be returned.  |  
| `includeArtifacts`  | `boolean`  | No  | Whether to include artifacts in the returned tasks. Defaults to false to reduce payload size.  |  
**Response:**
Result object for `ListTasks` method containing an array of tasks and pagination information.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tasks`  | array of [`Task`](https://a2a-protocol.org/latest/specification/#task)  | Yes  | Array of tasks matching the specified criteria.  |  
| `nextPageToken`  | `string`  | Yes  | A token to retrieve the next page of results, or empty if there are no more results in the list.  |  
| `pageSize`  | `integer`  | Yes  | The page size used for this response.  |  
| `totalSize`  | `integer`  | Yes  | Total number of tasks available (before pagination).  |  
#### 10.4.5. CancelTask[¶](https://a2a-protocol.org/latest/specification/#1045-canceltask "Permanent link")
Cancels a running task.
**Request:**
Represents a request for the `CancelTask` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Optional. Tenant ID, provided as a path parameter.  |  
| `id`  | `string`  | Yes  | The resource ID of the task to cancel.  |  
| `metadata`  | `object`  | No  | A flexible key-value map for passing additional context or parameters.  |  
**Response:** See [`Task`](https://a2a-protocol.org/latest/specification/#411-task) object definition.
#### 10.4.6. SubscribeToTask[¶](https://a2a-protocol.org/latest/specification/#1046-subscribetotask "Permanent link")
Subscribe to task updates via streaming. Returns `UnsupportedOperationError` if the task is in a terminal state.
**Request:**
Represents a request for the `SubscribeToTask` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Optional. Tenant ID, provided as a path parameter.  |  
| `id`  | `string`  | Yes  | The resource ID of the task to subscribe to.  |  
**Response:** Server streaming [`StreamResponse`](https://a2a-protocol.org/latest/specification/#stream-response) objects.
#### 10.4.7. CreateTaskPushNotificationConfig[¶](https://a2a-protocol.org/latest/specification/#1047-createtaskpushnotificationconfig "Permanent link")
Creates a push notification configuration for a task.
**Request:**
**Error:** Message `CreateTaskPushNotificationConfigRequest` not found.
**Response:** See [`PushNotificationConfig`](https://a2a-protocol.org/latest/specification/#431-pushnotificationconfig) object definition.
#### 10.4.8. GetTaskPushNotificationConfig[¶](https://a2a-protocol.org/latest/specification/#1048-gettaskpushnotificationconfig "Permanent link")
Retrieves an existing push notification configuration for a task.
**Request:**
Represents a request for the `GetTaskPushNotificationConfig` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Optional. Tenant ID, provided as a path parameter.  |  
| `taskId`  | `string`  | Yes  | The parent task resource ID.  |  
| `id`  | `string`  | Yes  | The resource ID of the configuration to retrieve.  |  
**Response:** See [`PushNotificationConfig`](https://a2a-protocol.org/latest/specification/#431-pushnotificationconfig) object definition.
#### 10.4.9. ListTaskPushNotificationConfigs[¶](https://a2a-protocol.org/latest/specification/#1049-listtaskpushnotificationconfigs "Permanent link")
Lists all push notification configurations for a task.
**Request:**
Represents a request for the `ListTaskPushNotificationConfigs` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Optional. Tenant ID, provided as a path parameter.  |  
| `taskId`  | `string`  | Yes  | The parent task resource ID.  |  
| `pageSize`  | `integer`  | No  | The maximum number of configurations to return.  |  
| `pageToken`  | `string`  | No  | A page token received from a previous `ListTaskPushNotificationConfigsRequest` call.  |  
**Response:**
Represents a successful response for the `ListTaskPushNotificationConfigs` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `configs`  | array of [`TaskPushNotificationConfig`](https://a2a-protocol.org/latest/specification/#taskpushnotificationconfig)  | No  | The list of push notification configurations.  |  
| `nextPageToken`  | `string`  | No  | A token to retrieve the next page of results, or empty if there are no more results in the list.  |  
#### 10.4.10. DeleteTaskPushNotificationConfig[¶](https://a2a-protocol.org/latest/specification/#10410-deletetaskpushnotificationconfig "Permanent link")
Removes a push notification configuration for a task.
**Request:**
Represents a request for the `DeleteTaskPushNotificationConfig` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Optional. Tenant ID, provided as a path parameter.  |  
| `taskId`  | `string`  | Yes  | The parent task resource ID.  |  
| `id`  | `string`  | Yes  | The resource ID of the configuration to delete.  |  
**Response:** `google.protobuf.Empty`
#### 10.4.11. GetExtendedAgentCard[¶](https://a2a-protocol.org/latest/specification/#10411-getextendedagentcard "Permanent link")
Retrieves the agent's extended capability card after authentication.
**Request:**
Represents a request for the `GetExtendedAgentCard` method.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Optional. Tenant ID, provided as a path parameter.  |  
**Response:** See [`AgentCard`](https://a2a-protocol.org/latest/specification/#441-agentcard) object definition.
### 10.5. gRPC-Specific Data Types[¶](https://a2a-protocol.org/latest/specification/#105-grpc-specific-data-types "Permanent link")
#### 10.5.1. TaskPushNotificationConfig[¶](https://a2a-protocol.org/latest/specification/#1051-taskpushnotificationconfig "Permanent link")
Resource wrapper for push notification configurations. This is a gRPC-specific type used in resource-oriented operations to provide the full resource name along with the configuration data.
A container associating a push notification configuration with a specific task.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Optional. Tenant ID.  |  
| `id`  | `string`  | No  | The push notification configuration details. A unique identifier (e.g. UUID) for this push notification configuration.  |  
| `taskId`  | `string`  | No  | The ID of the task this configuration is associated with.  |  
| `url`  | `string`  | Yes  | The URL where the notification should be sent.  |  
| `token`  | `string`  | No  | A token unique for this task or session.  |  
| `authentication`  | [`AuthenticationInfo`](https://a2a-protocol.org/latest/specification/#authenticationinfo)  | No  | Authentication information required to send the notification.  |  
**Fields:**
A container associating a push notification configuration with a specific task.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `tenant`  | `string`  | No  | Optional. Tenant ID.  |  
| `id`  | `string`  | No  | The push notification configuration details. A unique identifier (e.g. UUID) for this push notification configuration.  |  
| `taskId`  | `string`  | No  | The ID of the task this configuration is associated with.  |  
| `url`  | `string`  | Yes  | The URL where the notification should be sent.  |  
| `token`  | `string`  | No  | A token unique for this task or session.  |  
| `authentication`  | [`AuthenticationInfo`](https://a2a-protocol.org/latest/specification/#authenticationinfo)  | No  | Authentication information required to send the notification.  |  
### 10.6. Error Handling[¶](https://a2a-protocol.org/latest/specification/#106-error-handling "Permanent link")
gRPC error responses use the standard [gRPC status](https://grpc.io/docs/guides/error/) structure with [google.rpc.Status](https://github.com/googleapis/googleapis/blob/master/google/rpc/status.proto), which maps to the generic A2A error model defined in [Section 3.3.2](https://a2a-protocol.org/latest/specification/#332-error-handling) as follows:
  * **Error Code** : Mapped to `status.code` (gRPC status code enum)
  * **Error Message** : Mapped to `status.message` (human-readable string)
  * **Error Details** : Mapped to `status.details` (repeated google.protobuf.Any messages)


**A2A Error Representation:**
For A2A-specific errors, implementations **MUST** include a `google.rpc.ErrorInfo` message in the `status.details` array with:
  * `reason`: The A2A error type in UPPER_SNAKE_CASE without the "Error" suffix (e.g., `TASK_NOT_FOUND`)
  * `domain`: Set to `"a2a-protocol.org"`
  * `metadata`: Optional map of additional error context


For the complete mapping of A2A error types to gRPC status codes, see [Section 5.4 (Error Code Mappings)](https://a2a-protocol.org/latest/specification/#54-error-code-mappings).
**Error Response Example:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-54-1)// Standard gRPC invalid argument error
[](https://a2a-protocol.org/latest/specification/#__codelineno-54-2)status {
[](https://a2a-protocol.org/latest/specification/#__codelineno-54-3)  code: INVALID_ARGUMENT
[](https://a2a-protocol.org/latest/specification/#__codelineno-54-4)  message: "Invalid request parameters"
[](https://a2a-protocol.org/latest/specification/#__codelineno-54-5)  details: [
[](https://a2a-protocol.org/latest/specification/#__codelineno-54-6)    {
[](https://a2a-protocol.org/latest/specification/#__codelineno-54-7)      type: "type.googleapis.com/google.rpc.BadRequest"
[](https://a2a-protocol.org/latest/specification/#__codelineno-54-8)      field_violations: [
[](https://a2a-protocol.org/latest/specification/#__codelineno-54-9)        {
[](https://a2a-protocol.org/latest/specification/#__codelineno-54-10)          field: "message.parts"
[](https://a2a-protocol.org/latest/specification/#__codelineno-54-11)          description: "At least one part is required"
[](https://a2a-protocol.org/latest/specification/#__codelineno-54-12)        }
[](https://a2a-protocol.org/latest/specification/#__codelineno-54-13)      ]
[](https://a2a-protocol.org/latest/specification/#__codelineno-54-14)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-54-15)  ]
[](https://a2a-protocol.org/latest/specification/#__codelineno-54-16)}

```

**Example A2A-Specific Error Response:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-55-1)// A2A-specific task not found error
[](https://a2a-protocol.org/latest/specification/#__codelineno-55-2)status {
[](https://a2a-protocol.org/latest/specification/#__codelineno-55-3)  code: NOT_FOUND
[](https://a2a-protocol.org/latest/specification/#__codelineno-55-4)  message: "Task with ID 'task-123' not found"
[](https://a2a-protocol.org/latest/specification/#__codelineno-55-5)  details: [
[](https://a2a-protocol.org/latest/specification/#__codelineno-55-6)    {
[](https://a2a-protocol.org/latest/specification/#__codelineno-55-7)      type: "type.googleapis.com/google.rpc.ErrorInfo"
[](https://a2a-protocol.org/latest/specification/#__codelineno-55-8)      reason: "TASK_NOT_FOUND"
[](https://a2a-protocol.org/latest/specification/#__codelineno-55-9)      domain: "a2a-protocol.org"
[](https://a2a-protocol.org/latest/specification/#__codelineno-55-10)      metadata: {
[](https://a2a-protocol.org/latest/specification/#__codelineno-55-11)        task_id: "task-123"
[](https://a2a-protocol.org/latest/specification/#__codelineno-55-12)        timestamp: "2025-11-09T10:30:00Z"
[](https://a2a-protocol.org/latest/specification/#__codelineno-55-13)      }
[](https://a2a-protocol.org/latest/specification/#__codelineno-55-14)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-55-15)  ]
[](https://a2a-protocol.org/latest/specification/#__codelineno-55-16)}

```

### 10.7. Streaming[¶](https://a2a-protocol.org/latest/specification/#107-streaming "Permanent link")
gRPC streaming uses server streaming RPCs for real-time updates. The `StreamResponse` message provides a union of possible streaming events:
A wrapper object used in streaming operations to encapsulate different types of response data.  
| Field  | Type  | Required  | Description  |  
| --- | --- | --- | --- |  
| `task`  | [`Task`](https://a2a-protocol.org/latest/specification/#task)  | Optional (OneOf)  | A Task object containing the current state of the task.  |  
| `message`  | [`Message`](https://a2a-protocol.org/latest/specification/#message)  | Optional (OneOf)  | A Message object containing a message from the agent.  |  
| `statusUpdate`  | [`TaskStatusUpdateEvent`](https://a2a-protocol.org/latest/specification/#taskstatusupdateevent)  | Optional (OneOf)  | An event indicating a task status update.  |  
| `artifactUpdate`  | [`TaskArtifactUpdateEvent`](https://a2a-protocol.org/latest/specification/#taskartifactupdateevent)  | Optional (OneOf)  | An event indicating a task artifact update.  |  
**Note:** A `StreamResponse` MUST contain exactly one of the following: `task`, `message`, `statusUpdate`, `artifactUpdate`
## 11. HTTP+JSON/REST Protocol Binding[¶](https://a2a-protocol.org/latest/specification/#11-httpjsonrest-protocol-binding "Permanent link")
The HTTP+JSON protocol binding provides a RESTful interface using standard HTTP methods and JSON payloads.
### 11.1. Protocol Requirements[¶](https://a2a-protocol.org/latest/specification/#111-protocol-requirements "Permanent link")
  * **Protocol:** HTTP(S) with JSON payloads
  * **Content-Type:** `application/json` for requests and responses
  * **Methods:** Standard HTTP verbs (GET, POST, PUT, DELETE)
  * **URL Patterns:** RESTful resource-based URLs
  * **Streaming:** Server-Sent Events for real-time updates


### 11.2. Service Parameter Transmission[¶](https://a2a-protocol.org/latest/specification/#112-service-parameter-transmission "Permanent link")
A2A service parameters defined in [Section 3.2.6](https://a2a-protocol.org/latest/specification/#326-service-parameters) **MUST** be transmitted using standard HTTP request headers.
**Service Parameter Requirements:**
  * Service parameter names **MUST** be transmitted as HTTP header fields
  * Service parameter keys are case-insensitive per HTTP specification (RFC 9110)
  * Multiple values for the same service parameter (e.g., `A2A-Extensions`) **SHOULD** be comma-separated in a single header field


**Example Request with A2A Service Parameters:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-56-1)POST /message:send HTTP/1.1
[](https://a2a-protocol.org/latest/specification/#__codelineno-56-2)Host: agent.example.com
[](https://a2a-protocol.org/latest/specification/#__codelineno-56-3)Content-Type: application/json
[](https://a2a-protocol.org/latest/specification/#__codelineno-56-4)Authorization: Bearer token
[](https://a2a-protocol.org/latest/specification/#__codelineno-56-5)A2A-Version: 0.3
[](https://a2a-protocol.org/latest/specification/#__codelineno-56-6)A2A-Extensions: https://example.com/extensions/geolocation/v1,https://standards.org/extensions/citations/v1
[](https://a2a-protocol.org/latest/specification/#__codelineno-56-7)
[](https://a2a-protocol.org/latest/specification/#__codelineno-56-8){
[](https://a2a-protocol.org/latest/specification/#__codelineno-56-9)  "message": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-56-10)    "role": "ROLE_USER",
[](https://a2a-protocol.org/latest/specification/#__codelineno-56-11)    "parts": [{"text": "Find restaurants near me"}]
[](https://a2a-protocol.org/latest/specification/#__codelineno-56-12)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-56-13)}

```

### 11.3. URL Patterns and HTTP Methods[¶](https://a2a-protocol.org/latest/specification/#113-url-patterns-and-http-methods "Permanent link")
#### 11.3.1. Message Operations[¶](https://a2a-protocol.org/latest/specification/#1131-message-operations "Permanent link")
  * `POST /message:send` - Send message
  * `POST /message:stream` - Send message with streaming (SSE response)


#### 11.3.2. Task Operations[¶](https://a2a-protocol.org/latest/specification/#1132-task-operations "Permanent link")
  * `GET /tasks/{id}` - Get task status
  * `GET /tasks` - List tasks (with query parameters)
  * `POST /tasks/{id}:cancel` - Cancel task
  * `POST /tasks/{id}:subscribe` - Subscribe to task updates (SSE response, returns error for terminal tasks)


#### 11.3.3. Push Notification Configuration[¶](https://a2a-protocol.org/latest/specification/#1133-push-notification-configuration "Permanent link")
  * `POST /tasks/{id}/pushNotificationConfigs` - Create configuration
  * `GET /tasks/{id}/pushNotificationConfigs/{configId}` - Get configuration
  * `GET /tasks/{id}/pushNotificationConfigs` - List configurations
  * `DELETE /tasks/{id}/pushNotificationConfigs/{configId}` - Delete configuration


#### 11.3.4. Agent Card[¶](https://a2a-protocol.org/latest/specification/#1134-agent-card "Permanent link")
  * `GET /extendedAgentCard` - Get authenticated extended Agent Card


### 11.4. Request/Response Format[¶](https://a2a-protocol.org/latest/specification/#114-requestresponse-format "Permanent link")
All requests and responses use JSON objects structurally equivalent to the Protocol Buffer definitions.
**Example Send Message:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-57-1)POST /message:send
[](https://a2a-protocol.org/latest/specification/#__codelineno-57-2)Content-Type: application/json
[](https://a2a-protocol.org/latest/specification/#__codelineno-57-3)
[](https://a2a-protocol.org/latest/specification/#__codelineno-57-4){
[](https://a2a-protocol.org/latest/specification/#__codelineno-57-5)  "message": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-57-6)    "messageId": "uuid",
[](https://a2a-protocol.org/latest/specification/#__codelineno-57-7)    "role": "ROLE_USER",
[](https://a2a-protocol.org/latest/specification/#__codelineno-57-8)    "parts": [{"text": "Hello"}]
[](https://a2a-protocol.org/latest/specification/#__codelineno-57-9)  },
[](https://a2a-protocol.org/latest/specification/#__codelineno-57-10)  "configuration": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-57-11)    "acceptedOutputModes": ["text/plain"]
[](https://a2a-protocol.org/latest/specification/#__codelineno-57-12)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-57-13)}

```

**Referenced Objects:** [`SendMessageRequest`](https://a2a-protocol.org/latest/specification/#321-sendmessagerequest), [`Message`](https://a2a-protocol.org/latest/specification/#414-message)
**Response:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-58-1)HTTP/1.1 200 OK
[](https://a2a-protocol.org/latest/specification/#__codelineno-58-2)Content-Type: application/json
[](https://a2a-protocol.org/latest/specification/#__codelineno-58-3)
[](https://a2a-protocol.org/latest/specification/#__codelineno-58-4){
[](https://a2a-protocol.org/latest/specification/#__codelineno-58-5)  "task": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-58-6)    "id": "task-uuid",
[](https://a2a-protocol.org/latest/specification/#__codelineno-58-7)    "contextId": "context-uuid",
[](https://a2a-protocol.org/latest/specification/#__codelineno-58-8)    "status": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-58-9)      "state": "TASK_STATE_COMPLETED"
[](https://a2a-protocol.org/latest/specification/#__codelineno-58-10)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-58-11)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-58-12)}

```

**Referenced Objects:** [`Task`](https://a2a-protocol.org/latest/specification/#411-task)
### 11.5. Query Parameter Naming for Request Parameters[¶](https://a2a-protocol.org/latest/specification/#115-query-parameter-naming-for-request-parameters "Permanent link")
HTTP methods that do not support request bodies (GET, DELETE) **MUST** transmit operation request parameters as path parameters or query parameters. This section defines how to map Protocol Buffer field names to query parameter names.
**Naming Convention:**
Query parameter names **MUST** use `camelCase` to match the JSON serialization of Protocol Buffer field names. This ensures consistency with request bodies used in POST operations.
**Example Mappings:**  
| Protocol Buffer Field  | Query Parameter Name  | Example Usage  |  
| --- | --- | --- |  
| `context_id`  | `contextId`  | `?contextId=uuid`  |  
| `page_size`  | `pageSize`  | `?pageSize=50`  |  
| `page_token`  | `pageToken`  | `?pageToken=cursor`  |  
| `task_id`  | `taskId`  | `?taskId=uuid`  |  
**Usage Examples:**
List tasks with filtering:

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-59-1)GET /tasks?contextId=uuid&status=working&pageSize=50&pageToken=cursor

```

Get task with history:

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-60-1)GET /tasks/{id}?historyLength=10

```

**Field Type Handling:**
  * **Strings** : Passed directly as query parameter values
  * **Booleans** : Represented as lowercase strings (`true`, `false`)
  * **Numbers** : Represented as decimal strings
  * **Enums** : Represented using their string values (e.g., `status=working`)
  * **Repeated Fields** : Multiple values **MAY** be passed by repeating the parameter name (e.g., `?tag=value1&tag=value2`) or as comma-separated values (e.g., `?tag=value1,value2`)
  * **Nested Objects** : Not supported in query parameters; operations requiring nested objects **MUST** use POST with a request body
  * **Datetimes/Timestamps** : Represented as ISO 8601 strings (e.g., `2025-11-09T10:30:00Z`)


**URL Encoding:**
All query parameter values **MUST** be properly URL-encoded per [RFC 3986](https://www.rfc-editor.org/rfc/rfc3986.html).
### 11.6. Error Handling[¶](https://a2a-protocol.org/latest/specification/#116-error-handling "Permanent link")
HTTP error responses use the representation specified in [AIP-193](https://google.aip.dev/193#http11json-representation) which maps to the generic A2A error model defined in [Section 3.3.2](https://a2a-protocol.org/latest/specification/#332-error-handling) as follows:
  * **Error Code** : Mapped to the HTTP status code and the `error.code` field
  * **Error Message** : Mapped to the `error.message` field (human-readable string)
  * **Error Details** : Mapped to the `error.details` array (containing `google.protobuf.Any` messages)


**A2A Error Representation:**
For A2A-specific errors, implementations **MUST** include a `google.rpc.ErrorInfo` message in the `details` array with:
  * `@type`: Set to `"type.googleapis.com/google.rpc.ErrorInfo"`
  * `reason`: The A2A error type in UPPER_SNAKE_CASE without the "Error" suffix (e.g., `TASK_NOT_FOUND`)
  * `domain`: Set to `"a2a-protocol.org"`
  * `metadata`: Optional map of additional error context


For the complete mapping of A2A error types to HTTP status codes, see [Section 5.4 (Error Code Mappings)](https://a2a-protocol.org/latest/specification/#54-error-code-mappings). Additional error context **MAY** be included in the `details` array of the Status object.
**Error Response Example:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-1)HTTP/1.1 404 Not Found
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-2)Content-Type: application/json
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-3)
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-4){
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-5)  "error": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-6)    "code": 404,
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-7)    "status": "NOT_FOUND",
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-8)    "message": "The specified task ID does not exist or is not accessible",
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-9)    "details": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-10)      {
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-11)        "@type": "type.googleapis.com/google.rpc.ErrorInfo",
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-12)        "reason": "TASK_NOT_FOUND",
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-13)        "domain": "a2a-protocol.org",
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-14)        "metadata": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-15)          "taskId": "task-123",
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-16)          "timestamp": "2025-11-09T10:30:00.000Z"
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-17)        }
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-18)      }
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-19)    ]
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-20)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-61-21)}

```

Extension fields like `taskId` and `timestamp` provide additional context to help diagnose the error.
### 11.7. Streaming[¶](https://a2a-protocol.org/latest/specification/#117-streaming "Permanent link")
REST streaming uses Server-Sent Events with the `data` field containing JSON serializations of the protocol data objects:

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-62-1)POST /message:stream
[](https://a2a-protocol.org/latest/specification/#__codelineno-62-2)Content-Type: application/json
[](https://a2a-protocol.org/latest/specification/#__codelineno-62-3)
[](https://a2a-protocol.org/latest/specification/#__codelineno-62-4){ /* SendMessageRequest object */ }

```

**Referenced Objects:** [`SendMessageRequest`](https://a2a-protocol.org/latest/specification/#321-sendmessagerequest)
**Response:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-63-1)HTTP/1.1 200 OK
[](https://a2a-protocol.org/latest/specification/#__codelineno-63-2)Content-Type: text/event-stream
[](https://a2a-protocol.org/latest/specification/#__codelineno-63-3)
[](https://a2a-protocol.org/latest/specification/#__codelineno-63-4)data: { /* StreamResponse object */ }
[](https://a2a-protocol.org/latest/specification/#__codelineno-63-5)
[](https://a2a-protocol.org/latest/specification/#__codelineno-63-6)data: { /* StreamResponse object */ }

```

**Referenced Objects:** [`StreamResponse`](https://a2a-protocol.org/latest/specification/#323-stream-response) Streaming responses are simple, linearly ordered sequences: first a `Task` (or single `Message`), then zero or more status or artifact update events until the task reaches a terminal or interrupted state, at which point the stream closes. Implementations SHOULD avoid re-ordering events and MAY optionally resend a final `Task` snapshot before closing.
## 12. Custom Binding Guidelines[¶](https://a2a-protocol.org/latest/specification/#12-custom-binding-guidelines "Permanent link")
While the A2A protocol provides three standard bindings (JSON-RPC, gRPC, and HTTP+JSON/REST), implementers **MAY** create custom protocol bindings to support additional transport mechanisms or communication patterns. Custom bindings **MUST** comply with all requirements defined in [Section 5 (Protocol Binding Requirements and Interoperability)](https://a2a-protocol.org/latest/specification/#5-protocol-binding-requirements-and-interoperability). This section provides additional guidelines specific to developing custom bindings.
### 12.1. Binding Requirements[¶](https://a2a-protocol.org/latest/specification/#121-binding-requirements "Permanent link")
Custom protocol bindings **MUST** :
  1. **Implement All Core Operations** : Support all operations defined in [Section 3 (A2A Protocol Operations)](https://a2a-protocol.org/latest/specification/#3-a2a-protocol-operations)
  2. **Preserve Data Model** : Use data structures functionally equivalent to those defined in [Section 4 (Protocol Data Model)](https://a2a-protocol.org/latest/specification/#4-protocol-data-model)
  3. **Maintain Semantics** : Ensure operations behave consistently with the abstract operation definitions
  4. **Document Completely** : Provide comprehensive documentation of the binding specification


### 12.2. Data Type Mappings[¶](https://a2a-protocol.org/latest/specification/#122-data-type-mappings "Permanent link")
Custom bindings **MUST** provide clear mappings for:
  * **Protocol Buffer Types** : Define how each Protocol Buffer message type is represented
  * **Timestamps** : Follow the conventions in [Section 5.6.1 (Timestamps)](https://a2a-protocol.org/latest/specification/#561-timestamps)
  * **Binary Data** : Specify encoding for binary content (e.g., base64 for text-based protocols)
  * **Enumerations** : Define representation of enum values (e.g., strings, integers)


### 12.3. Service Parameter Transmission[¶](https://a2a-protocol.org/latest/specification/#123-service-parameter-transmission "Permanent link")
As specified in [Section 3.2.6 (Service Parameters)](https://a2a-protocol.org/latest/specification/#326-service-parameters), custom protocol bindings **MUST** document how service parameters are transmitted. The binding specification **MUST** address:
  1. **Transmission Mechanism** : The protocol-specific method for transmitting service parameter key-value pairs
  2. **Value Constraints** : Any limitations on service parameter values (e.g., character encoding, size limits)
  3. **Reserved Names** : Any service parameter names reserved by the binding itself
  4. **Fallback Strategy** : What happens when the protocol lacks native header support (e.g., passing service parameters in metadata)


**Example Documentation Requirements:**
  * **For native header support** : "Service parameters are transmitted using HTTP request headers. Service parameter keys are case-insensitive and must conform to RFC 7230. Service parameter values must be UTF-8 strings."
  * **For protocols without headers** : "Service parameters are serialized as a JSON object and transmitted in the request metadata field `a2a-service-parameters`."


### 12.4. Error Mapping[¶](https://a2a-protocol.org/latest/specification/#124-error-mapping "Permanent link")
Custom bindings **MUST** :
  1. **Map Standard Errors** : Provide mappings for all A2A-specific error types defined in [Section 3.2.2 (Error Handling)](https://a2a-protocol.org/latest/specification/#332-error-handling)
  2. **Preserve Error Information** : Ensure error details are accessible to clients
  3. **Use Appropriate Codes** : Map to protocol-native error codes where applicable
  4. **Document Error Format** : Specify the structure of error responses


### 12.5. Streaming Support[¶](https://a2a-protocol.org/latest/specification/#125-streaming-support "Permanent link")
If the binding supports streaming operations:
  1. **Define Stream Mechanism** : Document how streaming is implemented (e.g., WebSockets, long-polling, chunked encoding)
  2. **Event Ordering** : Specify ordering guarantees for streaming events
  3. **Reconnection** : Define behavior for connection interruption and resumption
  4. **Stream Termination** : Specify how stream completion is signaled


If streaming is not supported, the binding **MUST** clearly document this limitation in the Agent Card.
### 12.6. Authentication and Authorization[¶](https://a2a-protocol.org/latest/specification/#126-authentication-and-authorization "Permanent link")
Custom bindings **MUST** :
  1. **Support Standard Schemes** : Implement authentication schemes declared in the Agent Card
  2. **Document Integration** : Specify how credentials are transmitted in the protocol
  3. **Handle Challenges** : Define how authentication challenges are communicated
  4. **Maintain Security** : Follow security best practices for the transport protocol


### 12.7. Agent Card Declaration[¶](https://a2a-protocol.org/latest/specification/#127-agent-card-declaration "Permanent link")
Custom bindings **MUST** be declared in the Agent Card:
  1. **Transport Identifier** : Use a clear, descriptive transport name
  2. **Endpoint URL** : Provide the full URL where the binding is available
  3. **Documentation Link** : Include a URL to the complete binding specification


**Example:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-64-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-64-2)  "supportedInterfaces": [
[](https://a2a-protocol.org/latest/specification/#__codelineno-64-3)    {
[](https://a2a-protocol.org/latest/specification/#__codelineno-64-4)      "url": "wss://agent.example.com/a2a/websocket",
[](https://a2a-protocol.org/latest/specification/#__codelineno-64-5)      "protocolBinding": "WEBSOCKET"
[](https://a2a-protocol.org/latest/specification/#__codelineno-64-6)    }
[](https://a2a-protocol.org/latest/specification/#__codelineno-64-7)  ]
[](https://a2a-protocol.org/latest/specification/#__codelineno-64-8)}

```

### 12.8. Interoperability Testing[¶](https://a2a-protocol.org/latest/specification/#128-interoperability-testing "Permanent link")
Custom binding implementers **SHOULD** :
  1. **Test Against Reference** : Verify behavior matches standard bindings
  2. **Document Differences** : Clearly note any deviations from standard binding behavior
  3. **Provide Examples** : Include sample requests and responses
  4. **Test Edge Cases** : Verify handling of error conditions, large payloads, and long-running tasks


## 13. Security Considerations[¶](https://a2a-protocol.org/latest/specification/#13-security-considerations "Permanent link")
This section consolidates security guidance and best practices for implementing and operating A2A agents. For additional enterprise security considerations, see [Enterprise-Ready Features](https://a2a-protocol.org/latest/topics/enterprise-ready/).
### 13.1. Data Access and Authorization Scoping[¶](https://a2a-protocol.org/latest/specification/#131-data-access-and-authorization-scoping "Permanent link")
Implementations **MUST** ensure appropriate scope limitation based on the authenticated caller's authorization boundaries. This applies to all operations that access or list tasks and other resources.
**Authorization Principles:**
  * Servers **MUST** implement authorization checks on every [A2A Protocol Operations](https://a2a-protocol.org/latest/specification/#3-a2a-protocol-operations) request
  * Implementations **MUST** scope results to the caller's authorized access boundaries as defined by the agent's authorization model
  * Even when `contextId` or other filter parameters are not specified in requests, implementations **MUST** scope results to the caller's authorized access boundaries
  * Authorization models are agent-defined and **MAY** be based on:
    * User identity (user-based authorization)
    * Organizational roles or groups (role-based authorization)
    * Project or workspace membership (project-based authorization)
    * Organizational or tenant boundaries (multi-tenant authorization)
    * Custom authorization logic specific to the agent's domain


**Operations Requiring Scope Limitation:**
  * [`List Tasks`](https://a2a-protocol.org/latest/specification/#314-list-tasks): **MUST** only return tasks visible to the authenticated client according to the agent's authorization model
  * [`Get Task`](https://a2a-protocol.org/latest/specification/#313-get-task): **MUST** verify the authenticated client has access to the requested task according to the agent's authorization model
  * Task-related operations (Cancel, Subscribe, Push Notification Config): **MUST** verify the client has appropriate access rights according to the agent's authorization model


**Implementation Requirements:**
  * Authorization boundaries are defined by each agent's authorization model, not prescribed by the protocol
  * Authorization checks **MUST** occur before any database queries or operations that could leak information about the existence of resources outside the caller's authorization scope
  * Agents **SHOULD** document their authorization model and access control policies


See also: [Section 3.1.4 List Tasks (Security Note)](https://a2a-protocol.org/latest/specification/#314-list-tasks) for operation-specific requirements.
### 13.2. Push Notification Security[¶](https://a2a-protocol.org/latest/specification/#132-push-notification-security "Permanent link")
When implementing push notifications, both agents (as webhook callers) and clients (as webhook receivers) have security responsibilities.
**Agent (Webhook Caller) Requirements:**
  * Agents **MUST** include authentication credentials in webhook requests as specified in [`PushNotificationConfig.authentication`](https://a2a-protocol.org/latest/specification/#432-authenticationinfo)
  * Agents **SHOULD** implement reasonable timeout values for webhook requests (recommended: 10-30 seconds)
  * Agents **SHOULD** implement retry logic with exponential backoff for failed deliveries
  * Agents **MAY** stop attempting delivery after a configured number of consecutive failures
  * Agents **SHOULD** validate webhook URLs to prevent SSRF (Server-Side Request Forgery) attacks:
    * Reject private IP ranges (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
    * Reject localhost and link-local addresses
    * Implement URL allowlists where appropriate


**Client (Webhook Receiver) Requirements:**
  * Clients **MUST** validate webhook authenticity using the provided authentication credentials
  * Clients **SHOULD** verify the task ID in the payload matches an expected task they created
  * Clients **MUST** respond with HTTP 2xx status codes to acknowledge successful receipt
  * Clients **SHOULD** process notifications idempotently, as duplicate deliveries may occur
  * Clients **SHOULD** implement rate limiting to prevent webhook flooding
  * Clients **SHOULD** use HTTPS endpoints for webhook URLs to ensure confidentiality


**Configuration Security:**
  * Webhook URLs **SHOULD** use HTTPS to protect payload confidentiality in transit
  * Authentication tokens in [`PushNotificationConfig`](https://a2a-protocol.org/latest/specification/#431-pushnotificationconfig) **SHOULD** be treated as secrets and rotated periodically
  * Agents **SHOULD** securely store push notification configurations and credentials
  * Clients **SHOULD** use unique, single-purpose tokens for each push notification configuration


See also: [Section 4.3 Push Notification Objects](https://a2a-protocol.org/latest/specification/#43-push-notification-objects) and [Section 4.3.3 Push Notification Payload](https://a2a-protocol.org/latest/specification/#433-push-notification-payload).
### 13.3. Extended Agent Card Access Control[¶](https://a2a-protocol.org/latest/specification/#133-extended-agent-card-access-control "Permanent link")
The extended Agent Card feature allows agents to provide additional capabilities or information to authenticated clients beyond what is available in the public Agent Card.
**Access Control Requirements:**
  * The [`Get Extended Agent Card`](https://a2a-protocol.org/latest/specification/#3111-get-extended-agent-card) operation **MUST** require authentication
  * Agents **MUST** authenticate requests using one of the schemes declared in the public `AgentCard.securitySchemes` and `AgentCard.security` fields
  * Agents **MAY** return different extended card content based on the authenticated client's identity or authorization level
  * Agents **SHOULD** implement appropriate caching headers to control client-side caching of extended cards


**Capability-Based Access:**
  * Extended cards **MAY** include additional skills not present in the public card
  * Extended cards **MAY** expose more detailed capability information (e.g., rate limits, quotas)
  * Extended cards **MAY** include organization-specific or user-specific configuration
  * Agents **SHOULD** document which capabilities are available at different authentication levels


**Security Considerations:**
  * Extended cards **SHOULD NOT** include sensitive information that could be exploited if leaked (e.g., internal service URLs, unmasked credentials)
  * Agents **MUST** validate that clients have appropriate permissions before returning privileged information in extended cards
  * Clients retrieving extended cards **SHOULD** replace their cached public Agent Card with the extended version for the duration of their authenticated session
  * Agents **SHOULD** version extended cards appropriately and honor client cache invalidation


**Availability Declaration:**
  * Agents declare extended card support via `AgentCard.capabilities.extendedAgentCard`
  * When `capabilities.extendedAgentCard` is `false` or not present, the operation **MUST** return [`UnsupportedOperationError`](https://a2a-protocol.org/latest/specification/#332-error-handling)
  * When support is declared but no extended card is configured, the operation **MUST** return [`ExtendedAgentCardNotConfiguredError`](https://a2a-protocol.org/latest/specification/#332-error-handling)


See also: [Section 3.1.11 Get Extended Agent Card](https://a2a-protocol.org/latest/specification/#3111-get-extended-agent-card) and [Section 3.3.4 Capability Validation](https://a2a-protocol.org/latest/specification/#334-capability-validation).
### 13.4. General Security Best Practices[¶](https://a2a-protocol.org/latest/specification/#134-general-security-best-practices "Permanent link")
**Transport Security:**
  * Production deployments **MUST** use encrypted communication (HTTPS for HTTP-based bindings, TLS for gRPC)
  * Implementations **SHOULD** use modern TLS configurations (TLS 1.3+ recommended) with strong cipher suites
  * Agents **SHOULD** enforce HSTS (HTTP Strict Transport Security) headers when using HTTP-based bindings
  * Implementations **SHOULD** disable support for deprecated SSL/TLS versions (SSLv3, TLS 1.0, TLS 1.1)


**Input Validation:**
  * Agents **MUST** validate all input parameters before processing
  * Agents **SHOULD** implement appropriate limits on message sizes, file sizes, and request complexity
  * Agents **SHOULD** sanitize or validate file content types and reject unexpected media types


**Credential Management:**
  * API keys, tokens, and other credentials **MUST** be treated as secrets
  * Credentials **SHOULD** be rotated periodically
  * Credentials **SHOULD** be transmitted only over encrypted connections
  * Agents **SHOULD** implement credential revocation mechanisms
  * Agents **SHOULD** log authentication failures and implement rate limiting to prevent brute-force attacks


**Audit and Monitoring:**
  * Agents **SHOULD** log security-relevant events (authentication failures, authorization denials, suspicious requests)
  * Agents **SHOULD** implement monitoring for unusual patterns (rapid task creation, excessive cancellations)
  * Agents **SHOULD** provide audit trails for sensitive operations
  * Logs **MUST NOT** include sensitive information (credentials, personal data) unless required and properly protected


**Rate Limiting and Abuse Prevention:**
  * Agents **SHOULD** implement rate limiting on all operations
  * Agents **SHOULD** return appropriate error responses when rate limits are exceeded
  * Agents **MAY** implement different rate limits for different operations or user tiers


**Data Privacy:**
  * Agents **MUST** comply with applicable data protection regulations
  * Agents **SHOULD** provide mechanisms for users to request deletion of their data
  * Agents **SHOULD** implement appropriate data retention policies
  * Agents **SHOULD** minimize logging of sensitive or personal information


**Custom Binding Security:**
  * Custom protocol bindings **MUST** address security considerations in their specification
  * Custom bindings **SHOULD** follow the same security principles as standard bindings
  * Custom bindings **MUST** document authentication integration and credential transmission


See also: [Section 12.6 Authentication and Authorization (Custom Bindings)](https://a2a-protocol.org/latest/specification/#126-authentication-and-authorization).
## 14. IANA Considerations[¶](https://a2a-protocol.org/latest/specification/#14-iana-considerations "Permanent link")
This section provides registration templates for the A2A protocol's media type, HTTP headers, and well-known URI, intended for submission to the Internet Assigned Numbers Authority (IANA).
### 14.1. Media Type Registration[¶](https://a2a-protocol.org/latest/specification/#141-media-type-registration "Permanent link")
#### 14.1.1. application/a2a+json[¶](https://a2a-protocol.org/latest/specification/#1411-applicationa2ajson "Permanent link")
**Type name:** `application`
**Subtype name:** `a2a+json`
**Required parameters:** None
**Optional parameters:**
  * None


**Encoding considerations:** Binary (UTF-8 encoding MUST be used for JSON text)
**Security considerations:** This media type shares security considerations common to all JSON-based formats as described in RFC 8259, Section 12. Additionally:
  * Content MUST be validated against the A2A protocol schema before processing
  * Implementations MUST sanitize user-provided content to prevent injection attacks
  * File references within A2A messages MUST be validated to prevent server-side request forgery (SSRF)
  * Authentication and authorization MUST be enforced as specified in Section 7 of the A2A specification
  * Sensitive information in task history and artifacts MUST be protected according to applicable data protection regulations


**Interoperability considerations:** The A2A protocol supports multiple protocol bindings. This media type is intended for the HTTP+JSON/REST binding.
**Published specification:** Agent2Agent (A2A) Protocol Specification, available at: <https://a2a-protocol.org/latest/specification>
**Applications that use this media type:** AI agent platforms, agentic workflow systems, multi-agent collaboration tools, and enterprise automation systems that implement the A2A protocol for agent-to-agent communication.
**Fragment identifier considerations:** None
**Additional information:**
  * **Deprecated alias names for this type:** None
  * **Magic number(s):** None
  * **File extension(s):** .a2a.json
  * **Macintosh file type code(s):** TEXT


**Person & email address to contact for further information:** A2A Protocol Working Group, a2a-protocol@example.org
**Intended usage:** COMMON
**Restrictions on usage:** None
**Author:** A2A Protocol Working Group
**Change controller:** A2A Protocol Working Group
**Provisional registration:** No
### 14.2. HTTP Header Field Registrations[¶](https://a2a-protocol.org/latest/specification/#142-http-header-field-registrations "Permanent link")
**Note:** The following HTTP headers represent the HTTP-based protocol binding implementation of the abstract A2A service parameters defined in [Section 3.2.6](https://a2a-protocol.org/latest/specification/#326-service-parameters). These registrations are specific to HTTP/HTTPS transports.
#### 14.2.1. A2A-Version Header[¶](https://a2a-protocol.org/latest/specification/#1421-a2a-version-header "Permanent link")
**Header field name:** A2A-Version
**Applicable protocol:** HTTP
**Status:** Standard
**Author/Change controller:** A2A Protocol Working Group
**Specification document:** Section 3.2.5 of the A2A Protocol Specification
**Related information:** The A2A-Version header field indicates the A2A protocol version that the client is using. The value MUST be in the format `Major.Minor` (e.g., "0.3"). If the version is not supported by the agent, the agent returns a `VersionNotSupportedError`.
**Example:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-65-1)A2A-Version: 0.3

```

#### 14.2.2. A2A-Extensions Header[¶](https://a2a-protocol.org/latest/specification/#1422-a2a-extensions-header "Permanent link")
**Header field name:** A2A-Extensions
**Applicable protocol:** HTTP
**Status:** Standard
**Author/Change controller:** A2A Protocol Working Group
**Specification document:** Section 3.2.5 of the A2A Protocol Specification
**Related information:** The A2A-Extensions header field contains a comma-separated list of extension URIs that the client wants to use for the request. Extensions allow agents to provide additional functionality beyond the core A2A specification while maintaining backward compatibility.
**Example:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-66-1)A2A-Extensions: https://example.com/extensions/geolocation/v1,https://standards.org/extensions/citations/v1

```

### 14.3. Well-Known URI Registration[¶](https://a2a-protocol.org/latest/specification/#143-well-known-uri-registration "Permanent link")
**URI suffix:** agent-card.json
**Change controller:** A2A Protocol Working Group
**Specification document:** Section 8.2 of the A2A Protocol Specification
**Related information:** The `.well-known/agent-card.json` URI provides a standardized location for discovering an A2A agent's capabilities, supported protocols, authentication requirements, and available skills. The resource at this URI MUST return an AgentCard object as defined in Section 4.4.1 of the A2A specification.
**Status:** Permanent
**Security considerations:**
  * The Agent Card MAY contain public information about an agent's capabilities and SHOULD NOT include sensitive credentials or internal implementation details
  * Implementations SHOULD support HTTPS to ensure authenticity and integrity of the Agent Card
  * Agent Cards MAY be signed using JSON Web Signatures (JWS) as specified in the AgentCardSignature object (Section 4.4.7)
  * Clients SHOULD verify signatures when present to ensure the Agent Card has not been tampered with
  * Extended Agent Cards retrieved via authenticated endpoints (Section 3.1.11) MAY contain additional information and MUST enforce appropriate access controls


**Example:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-67-1)https://agent.example.com/.well-known/agent-card.json

```

* * *
## Appendix A. Migration & Legacy Compatibility[¶](https://a2a-protocol.org/latest/specification/#appendix-a-migration-legacy-compatibility "Permanent link")
This appendix catalogs renamed protocol messages and objects, their legacy identifiers, and the planned deprecation/removal schedule. All legacy names and anchors MUST remain resolvable until the stated earliest removal version.  
| Legacy Name  | Current Name  | Earliest Removal Version  | Notes  |  
| --- | --- | --- | --- |  
| `MessageSendParams`  | `SendMessageRequest`  | >= 0.5.0  | Request payload rename for clarity (request vs params)  |  
| `SendMessageSuccessResponse`  | `SendMessageResponse`  | >= 0.5.0  | Unified success response naming  |  
| `SendStreamingMessageSuccessResponse`  | `StreamResponse`  | >= 0.5.0  | Shorter, binding-agnostic streaming response  |  
| `SetTaskPushNotificationConfigRequest`  | `CreateTaskPushNotificationConfigRequest`  | >= 0.5.0  | Explicit creation intent  |  
| `ListTaskPushNotificationConfigSuccessResponse`  | `ListTaskPushNotificationConfigsResponse`  | >= 0.5.0  | Consistent response suffix removal  |  
| `GetAuthenticatedExtendedCardRequest`  | `GetExtendedAgentCardRequest`  | >= 0.5.0  | Removed "Authenticated" from naming  |  
Planned Lifecycle (example timeline; adjust per release strategy):
  1. 0.3.x: New names introduced; legacy names documented; aliases added.
  2. 0.4.x: Legacy names marked "deprecated" in SDKs and schemas; warning notes added.
  3. =0.5.0: Legacy names eligible for removal after review; migration appendix updated.


### A.1 Legacy Documentation Anchors[¶](https://a2a-protocol.org/latest/specification/#a1-legacy-documentation-anchors "Permanent link")
Hidden anchor spans preserve old inbound links:
Each legacy span SHOULD be placed adjacent to the current object's heading (to be inserted during detailed object section edits). If an exact numeric-prefixed anchor existed (e.g., `#414-message`), add an additional span matching that historical form if known.
### A.2 Migration Guidance[¶](https://a2a-protocol.org/latest/specification/#a2-migration-guidance "Permanent link")
Client Implementations SHOULD:
  * Prefer new names immediately for all new integrations.
  * Implement dual-handling where schemas/types permit (e.g., union type or backward-compatible decoder).
  * Log a warning when receiving legacy-named objects after the first deprecation announcement release.


Server Implementations MAY:
  * Accept both legacy and current request message forms during the overlap period.
  * Emit only current form in responses (recommended) while providing explicit upgrade notes.


#### A.2.1 Breaking Change: Kind Discriminator Removed[¶](https://a2a-protocol.org/latest/specification/#a21-breaking-change-kind-discriminator-removed "Permanent link")
**Version 1.0 introduces a breaking change** in how polymorphic objects are represented in the protocol. This affects `Part` types and streaming event types.
**Legacy Pattern (v0.3.x):** Objects used an inline `kind` field as a discriminator to identify the object type:
**Example 1 - TextPart:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-68-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-68-2)  "kind": "text",
[](https://a2a-protocol.org/latest/specification/#__codelineno-68-3)  "text": "Hello, world!"
[](https://a2a-protocol.org/latest/specification/#__codelineno-68-4)}

```

**Example 2 - FilePart:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-69-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-69-2)  "kind": "file",
[](https://a2a-protocol.org/latest/specification/#__codelineno-69-3)  "file": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-69-4)    "name": "diagram.png",
[](https://a2a-protocol.org/latest/specification/#__codelineno-69-5)    "mimeType": "image/png",
[](https://a2a-protocol.org/latest/specification/#__codelineno-69-6)    "fileWithBytes": "iVBORw0KGgo..."
[](https://a2a-protocol.org/latest/specification/#__codelineno-69-7)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-69-8)}

```

**Current Pattern (v1.0):** Objects now use the **JSON member name** itself to identify the type. The member name acts as the discriminator, and the value structure depends on the specific type:
**Example 1 - TextPart:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-70-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-70-2)  "text": "Hello, world!"
[](https://a2a-protocol.org/latest/specification/#__codelineno-70-3)}

```

**Example 2 - FilePart:**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-71-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-71-2)  "raw": "iVBORw0KGgo...",
[](https://a2a-protocol.org/latest/specification/#__codelineno-71-3)  "filename": "diagram.png",
[](https://a2a-protocol.org/latest/specification/#__codelineno-71-4)  "mediaType": "image/png"
[](https://a2a-protocol.org/latest/specification/#__codelineno-71-5)}

```

**Affected Types:**
  1. **Part Union Types** :
  2. **TextPart** :
     * **Legacy:** `{ "kind": "text", "text": "..." }`
     * **Current:** `{ "text": "..." }` (member presence acts as discriminator)
  3. **FilePart** :
     * **Legacy:** `{ "kind": "file", "file": { "name": "...", "mimeType": "...", "fileWithBytes": "..." } }`
     * **Current:** `{ "raw": "...", "filename": "...", "mediaType": "..." }` (or `url` instead of `raw`)
  4. **DataPart** :
     * **Legacy:** `{ "kind": "data", "data": {...} }`
     * **Current:** `{ "data": {...}, "mediaType": "application/json" }`
  5. **Streaming Event Types** :
  6. **TaskStatusUpdateEvent** :
     * **Legacy:** `{ "kind": "status-update", "taskId": "...", "status": {...} }`
     * **Current:** `{ "statusUpdate": { "taskId": "...", "status": {...} } }`
  7. **TaskArtifactUpdateEvent** :
     * **Legacy:** `{ "kind": "artifact-update", "taskId": "...", "artifact": {...} }`
     * **Current:** `{ "artifactUpdate": { "taskId": "...", "artifact": {...} } }`


**Migration Strategy:**
For **Clients** upgrading from pre-0.3.x:
  1. Update parsers to expect wrapper objects with member names as discriminators
  2. When constructing requests, use the new wrapper format
  3. Implement version detection based on the agent's `protocolVersions` in the `AgentCard`
  4. Consider maintaining backward compatibility by detecting and handling both formats during a transition period


For **Servers** upgrading from pre-0.3.x:
  1. Update serialization logic to emit wrapper objects
  2. **Breaking:** The `kind` field is no longer part of the protocol and should not be emitted
  3. Update deserialization to expect wrapper objects with member names
  4. Ensure the `AgentCard` declares the correct `protocolVersions` (e.g., ["1.0"] or later)


**Rationale:**
This change aligns with modern API design practices and Protocol Buffers' `oneof` semantics, where the field name itself serves as the type discriminator. This approach:
  * Reduces redundancy (no need for both a field name and a `kind` value)
  * Aligns JSON-RPC and gRPC representations more closely
  * Simplifies code generation from schema definitions
  * Eliminates the need for representing inheritance structures in schema languages
  * Improves type safety in strongly-typed languages


#### A.2.2 Breaking Change: Extended Agent Card Field Relocated[¶](https://a2a-protocol.org/latest/specification/#a22-breaking-change-extended-agent-card-field-relocated "Permanent link")
**Version 1.0 relocates the extended agent card capability** from a top-level field to the capabilities object for architectural consistency.
**Legacy Structure (pre-1.0):**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-72-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-72-2)  "supportsExtendedAgentCard": true,
[](https://a2a-protocol.org/latest/specification/#__codelineno-72-3)  "capabilities": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-72-4)    "streaming": true
[](https://a2a-protocol.org/latest/specification/#__codelineno-72-5)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-72-6)}

```

**Current Structure (1.0+):**

```
[](https://a2a-protocol.org/latest/specification/#__codelineno-73-1){
[](https://a2a-protocol.org/latest/specification/#__codelineno-73-2)  "capabilities": {
[](https://a2a-protocol.org/latest/specification/#__codelineno-73-3)    "streaming": true,
[](https://a2a-protocol.org/latest/specification/#__codelineno-73-4)    "extendedAgentCard": true
[](https://a2a-protocol.org/latest/specification/#__codelineno-73-5)  }
[](https://a2a-protocol.org/latest/specification/#__codelineno-73-6)}

```

**Proto Changes:**
  * Removed: `AgentCard.supports_extended_agent_card` (field 13)
  * Added: `AgentCapabilities.extended_agent_card` (field 5)


**Migration Steps:**
For **Agent Implementations** :
  1. Remove `supportsExtendedAgentCard` from top-level AgentCard
  2. Add `extendedAgentCard` to `capabilities` object
  3. Update validation: `agentCard.capabilities?.extendedAgentCard`


For **Client Implementations** :
  1. Update capability checks: `agentCard.capabilities?.extendedAgentCard`
  2. Temporary fallback (transition period):



```
[](https://a2a-protocol.org/latest/specification/#__codelineno-74-1)const supported = agentCard.capabilities?.extendedAgentCard ||
[](https://a2a-protocol.org/latest/specification/#__codelineno-74-2)                  agentCard.supportsExtendedAgentCard;

```

  1. Remove fallback after agent ecosystem migrates


For **SDK Developers** :
  1. Regenerate code from updated proto
  2. Update type definitions
  3. Document breaking change in release notes


**Rationale:**
All optional features enabling specific operations (`streaming`, `pushNotifications`, `stateTransitionHistory`) reside in `AgentCapabilities`. Moving `extendedAgentCard` achieves:
  * Architectural consistency
  * Improved discoverability
  * Semantic correctness (it is a capability)


### A.3 Future Automation[¶](https://a2a-protocol.org/latest/specification/#a3-future-automation "Permanent link")
Once the proto?schema generation pipeline lands, this appendix will be partially auto-generated (legacy mapping table sourced from a maintained manifest). Until then, edits MUST be manual and reviewed in PRs affecting `a2a.proto`.
## Appendix B. Relationship to MCP (Model Context Protocol)[¶](https://a2a-protocol.org/latest/specification/#appendix-b-relationship-to-mcp-model-context-protocol "Permanent link")
A2A and MCP are complementary protocols designed for different aspects of agentic systems:
  * **[Model Context Protocol (MCP)](https://modelcontextprotocol.io/):** Focuses on standardizing how AI models and agents connect to and interact with **tools, APIs, data sources, and other external resources.** It defines structured ways to describe tool capabilities (like function calling in LLMs), pass inputs, and receive structured outputs. Think of MCP as the "how-to" for an agent to _use_ a specific capability or access a resource.
  * **Agent2Agent Protocol (A2A):** Focuses on standardizing how independent, often opaque, **AI agents communicate and collaborate with each other as peers.** A2A provides an application-level protocol for agents to discover each other, negotiate interaction modalities, manage shared tasks, and exchange conversational context or complex results. It's about how agents _partner_ or _delegate_ work.


**How they work together:** An A2A Client agent might request an A2A Server agent to perform a complex task. The Server agent, in turn, might use MCP to interact with several underlying tools, APIs, or data sources to gather information or perform actions necessary to fulfill the A2A task.
For a more detailed comparison, see the [A2A and MCP guide](https://a2a-protocol.org/latest/topics/a2a-and-mcp/).
* * *
[ Previous  Next Steps  ](https://a2a-protocol.org/latest/tutorials/python/8-next-steps/) [ Next  What's New in v1.0  ](https://a2a-protocol.org/latest/whats-new-v1/)
Copyright 2026 The Linux Foundation. Licensed under the Apache License, Version 2.0. 
Made with [ Material for MkDocs ](https://squidfunk.github.io/mkdocs-material/)

