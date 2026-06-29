/**
 * Shared runtime for every iFLYTEK node: builds the argv for a skill script,
 * maps canonical credentials onto the script's env vars (the same shim as
 * core/credentials.py), and runs it via child_process.spawn.
 */
import { spawn } from 'child_process';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

export interface ArgSpec {
	name: string;
	flag?: string; // undefined => positional
	type: 'string' | 'integer' | 'number' | 'boolean' | 'enum';
	isOutputPath?: boolean;
}

export type CredProfile = 'xfei' | 'xfyun' | 'ifly' | 'composite' | 'none';

export interface SkillSpec {
	toolName: string;
	script: string; // repo-root-relative, e.g. skills/iflytek-translate/scripts/translate.py
	subcommand?: string;
	credProfile: CredProfile;
	output: 'stdout_text' | 'file' | 'json' | 'async_task';
	args: ArgSpec[];
}

export interface IflyCredentials {
	appId: string;
	apiKey: string;
	apiSecret: string;
}

const PREFIX: Record<string, string> = { xfei: 'XFEI', xfyun: 'XFYUN', ifly: 'IFLY' };

export function resolveEnv(profile: CredProfile, creds: IflyCredentials): Record<string, string> {
	if (profile === 'none') return {};
	if (profile in PREFIX) {
		const p = PREFIX[profile];
		return {
			[`${p}_APP_ID`]: creds.appId,
			[`${p}_API_KEY`]: creds.apiKey,
			[`${p}_API_SECRET`]: creds.apiSecret,
		};
	}
	if (profile === 'composite') {
		return {
			LLM_API_KEY: creds.apiKey,
			OCR_API_KEY: creds.apiKey,
			TRANSLATE_API_KEY: creds.apiKey,
		};
	}
	return {};
}

/**
 * Repo-root-equivalent dir that contains the `skills/` tree. SkillSpec.script
 * is repo-root-relative (e.g. skills/iflytek-translate/scripts/translate.py).
 * Defaults to the package root (where bundle-skills.js copies `skills/` at
 * build time); override with IFLY_SKILLS_ROOT to point at a local checkout.
 * At runtime __dirname is <package>/dist/nodes/shared, so three levels up.
 */
export function skillsRoot(): string {
	if (process.env.IFLY_SKILLS_ROOT) return process.env.IFLY_SKILLS_ROOT;
	return path.join(__dirname, '..', '..', '..');
}

function suffixFor(spec: ArgSpec, params: Record<string, unknown>): string {
	const fmt = params['format'];
	if (typeof fmt === 'string' && fmt && !fmt.includes(',')) return `.${fmt}`;
	return '.mp3';
}

export function buildArgv(
	spec: SkillSpec,
	params: Record<string, unknown>,
): { argv: string[]; managedOutput?: string } {
	const script = path.join(skillsRoot(), spec.script);
	const positionals: string[] = [];
	const options: string[] = [];
	let managedOutput: string | undefined;

	for (const arg of spec.args) {
		if (arg.isOutputPath) {
			let value = params[arg.name] as string | undefined;
			if (!value) {
				value = path.join(os.tmpdir(), `iflyskill_${Date.now()}${suffixFor(arg, params)}`);
			}
			managedOutput = value;
			if (arg.flag) options.push(arg.flag, value);
			continue;
		}
		const value = params[arg.name];
		if (value === undefined || value === null || value === '') continue;

		if (arg.type === 'boolean') {
			if (value && arg.flag) options.push(arg.flag);
		} else if (!arg.flag) {
			positionals.push(String(value));
		} else {
			options.push(arg.flag, String(value));
		}
	}

	const argv = [script];
	if (spec.subcommand) argv.push(spec.subcommand);
	return { argv: [...argv, ...positionals, ...options], managedOutput };
}

export interface RunResult {
	ok: boolean;
	code: number;
	stdout: string;
	stderr: string;
	artifactPath?: string;
}

export function runSkill(
	spec: SkillSpec,
	params: Record<string, unknown>,
	creds: IflyCredentials,
): Promise<RunResult> {
	const { argv, managedOutput } = buildArgv(spec, params);
	const pythonBin = process.env.PYTHON_BIN || (process.platform === 'win32' ? 'python' : 'python3');
	const env = { ...process.env, ...resolveEnv(spec.credProfile, creds), PYTHONIOENCODING: 'utf-8' };

	return new Promise((resolve) => {
		const child = spawn(pythonBin, argv, { env });
		let stdout = '';
		let stderr = '';
		child.stdout.on('data', (d) => (stdout += d.toString()));
		child.stderr.on('data', (d) => (stderr += d.toString()));
		child.on('error', (err) => resolve({ ok: false, code: -1, stdout, stderr: String(err) }));
		child.on('close', (code) => {
			let artifactPath: string | undefined;
			if (spec.output === 'file' && managedOutput && fs.existsSync(managedOutput)) {
				artifactPath = managedOutput;
			}
			resolve({ ok: code === 0, code: code ?? -1, stdout, stderr, artifactPath });
		});
	});
}
