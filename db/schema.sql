create table if not exists trainers (
    id integer generated always as identity primary key,
    name varchar not null,
    team_path varchar not null,
    model_path varchar not null,
    rating integer not null default 1000,
    created_at timestamp not null default now()
);

create table if not exists matches (
    id integer generated always as identity primary key,
    trainer_1 integer not null,
    trainer_2 integer not null,
    winner integer,
    created_at timestamp not null default now(),
    constraint fk_matches_trainer_1
        foreign key (trainer_1) references trainers(id),
    constraint fk_matches_trainer_2
        foreign key (trainer_2) references trainers(id),
    constraint fk_matches_winner
        foreign key (winner) references trainers(id),
    constraint chk_different_trainers
        check (trainer_1 <> trainer_2)
);
