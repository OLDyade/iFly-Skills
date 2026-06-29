import type { ICredentialType, INodeProperties } from 'n8n-workflow';

/**
 * Canonical iFLYTEK credentials, shared by every node. The per-node runtime
 * maps these onto the XFEI_, XFYUN_, or IFLY_ env vars each skill script expects.
 */
export class IflyApi implements ICredentialType {
	name = 'iflyApi';

	displayName = 'iFLYTEK API';

	documentationUrl = 'https://www.xfyun.cn/doc/';

	properties: INodeProperties[] = [
		{
			displayName: 'App ID',
			name: 'appId',
			type: 'string',
			default: '',
			required: true,
		},
		{
			displayName: 'API Key',
			name: 'apiKey',
			type: 'string',
			typeOptions: { password: true },
			default: '',
			required: true,
		},
		{
			displayName: 'API Secret',
			name: 'apiSecret',
			type: 'string',
			typeOptions: { password: true },
			default: '',
			required: true,
		},
	];
}
