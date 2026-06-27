const manifest = (() => {
function __memo(fn) {
	let value;
	return () => value ??= (value = fn());
}

return {
	appDir: "_app",
	appPath: "_app",
	assets: new Set([]),
	mimeTypes: {},
	_: {
		client: {start:"_app/immutable/entry/start.BQl8YRlJ.js",app:"_app/immutable/entry/app.D6x0r5wX.js",imports:["_app/immutable/entry/start.BQl8YRlJ.js","_app/immutable/chunks/hk9RpYrw.js","_app/immutable/chunks/ClyAy-cy.js","_app/immutable/chunks/C6fsqCF9.js","_app/immutable/entry/app.D6x0r5wX.js","_app/immutable/chunks/CUvxg_Ft.js","_app/immutable/chunks/ClyAy-cy.js","_app/immutable/chunks/C6fsqCF9.js","_app/immutable/chunks/BIE8nj0Q.js","_app/immutable/chunks/BI0rD3Mt.js"],stylesheets:[],fonts:[],uses_env_dynamic_public:false},
		nodes: [
			__memo(() => import('./chunks/0-P1408MlE.js')),
			__memo(() => import('./chunks/1-UicIlhTF.js')),
			__memo(() => import('./chunks/2-Dui6HgsZ.js').then(function (n) { return n._; }))
		],
		remotes: {
			
		},
		routes: [
			{
				id: "/[...catchall]",
				pattern: /^(?:\/([^]*))?\/?$/,
				params: [{"name":"catchall","optional":false,"rest":true,"chained":true}],
				page: { layouts: [0,], errors: [1,], leaf: 2 },
				endpoint: null
			}
		],
		prerendered_routes: new Set([]),
		matchers: async () => {
			
			return {  };
		},
		server_assets: {}
	}
}
})();

const prerendered = new Set([]);

const base = "";

export { base, manifest, prerendered };
//# sourceMappingURL=manifest.js.map
