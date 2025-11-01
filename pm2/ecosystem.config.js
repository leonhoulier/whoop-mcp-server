module.exports = {
  apps: [
    {
      name: 'whoop-mcp-http',
      script: './start_whoop_mcp_http.sh',
      cwd: '/path/to/whoop-mcp-server',
      interpreter: 'bash',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production',
        MCP_HTTP_PORT: '8003'
      },
      error_file: './logs/whoop-mcp-http-error.log',
      out_file: './logs/whoop-mcp-http-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true
    },
    {
      name: 'whoop-docs',
      script: './start_whoop_docs.sh',
      cwd: '/path/to/whoop-mcp-server',
      interpreter: 'bash',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      env: {
        NODE_ENV: 'production',
        WHOOP_DOCS_PORT: '8005'
      },
      error_file: './logs/whoop-docs-error.log',
      out_file: './logs/whoop-docs-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true
    }
  ]
};
