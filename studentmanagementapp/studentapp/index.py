from studentapp import create_app

app = create_app("default")

if __name__ == '__main__':
    app.run(debug=True, port=5001)
