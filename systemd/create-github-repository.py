import github, sys, argparse

def parse_cli_args():
    parser = argparse.ArgumentParser(description='create-github-repository')
    parser.add_argument('token', help='Github OAuth token')
    parser.add_argument('name', help='Name of the repository')
    return parser.parse_args()

def main():
    args = parse_cli_args()
    g = github.Github(args.token)
    user = g.get_user()

    try:
        r = user.create_repo(args.name)
    except:
        print("Unable to create repository {}".format(args.name))
        raise
        
if __name__ == "__main__":
    main()