import os

import crontab


def create_task():
    cron = crontab.CronTab(user=True)

    task = cron.new(
        command=f"/usr/bin/docker compose --file {os.getcwd()}/docker-compose.yml up --build >> {os.getcwd()}/strompris.log 2>&1"
    )
    task.hour.on(19)
    task.minute.on(0)

    if task.valid:
        print(task)
        cron.write()
    else:
        print("Oops")


def main():
    create_task()


if __name__ == "__main__":
    main()
