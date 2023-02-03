# Input Form

The "Soirée Italienne" application had special UI requirements, so I made a Fable/Elmish app to inject the generated JavaScript into the registration page.

## Building and running the app

To build locally and start the webpack-devserver (instructions taken from the [sample-react-counter](https://github.com/elmish/sample-react-counter) project, hence I added their [license](LICENSE.md) to this directory as I used their build setup nearly verbatim):
* once: `dotnet tool restore`
* `dotnet fake build -t Watch`

open [localhost:8090](http://localhost:8090)

### VS Code

If you happen to use Visual Studio Code, simply hitting F5 will start the development watch mode for you and opens your default browser navigating to [localhost:8090](http://localhost:8090).
