const path = require("path")

module.exports = (env, argv) => {
    // extract build mode from command-line
    const mode = argv.mode;
    const result = {
        mode: mode,
        entry: "./src/App.fsproj",
        module: {
            rules: [{
                test: /\.fs(x|proj)?$/,
                use: "fable-loader"
            }]
        }
    }

    if ("development" == mode) {
        Object.assign(
            result, {
                devtool: "eval-source-map",

                devServer: {
                    devMiddleware: {
                        publicPath: "/"
                    },
                    port: 8081,
                    proxy: undefined,
                    hot: true,
                    static: {
                        directory: path.resolve(__dirname, "./dist"),
                        staticOptions: {},
                    },
                },
            });
    }

    return result;
}
