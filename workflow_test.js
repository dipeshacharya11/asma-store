export const meta = {
  name: 'test-migration',
  description: 'Test running a command',
  phases: [{ title: 'Run', detail: 'Run a simple command' }]
};

phase('Run');
const result = await agent('echo hello', {label: 'test'});
log(`Result: ${result}`);