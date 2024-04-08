-- Stats
select 'PB', count(*) AS pb from factures f
where abs(total-cumul)>0.001
UNION
select 'all', count(*) AS ok from factures f
UNION
select 'zero', count(*) AS ok from factures f where total=0.0

select count(*) from produits;

-- produits même prix similaires...
select p1.price,p1.name ,p2.name  from produits p1,produits p2
where p1.price =p2.price AND p1.name <p2.name
ORDER BY p1.name ;

select count(*) from clients;
select cat as catégorie, count(*) as 'Nbre clients' from clients group by cat;

-- résumé par année -> graph
SELECT count(*) AS N, round(sum(total),2) AS CA, substr(dt,0,5) AS Year
from factures
group by Year;

-- résumé par mois -> graph
SELECT count(*) AS N, round(sum(total),2) AS CA, substr(dt,0,8) AS YM
from factures
group by YM;

-- résumé par jour -> graph (day of week 1-7 with Monday==1)
SELECT count(*) AS N, round(sum(total),2) AS CA, strftime('%w', dt) AS Day
from factures
group by Day;


-- Factures avec cumul incorrect
select no, total, cumul, abs(total-cumul) AS diff from factures where diff>0.01 order by no;
delete from factures where abs(total-cumul)>0.01;


select * from clients where cat='A' and adr='';

-- factures à total/cumul nul
select * from factures where total=0.0 or cumul=0.0;
delete from factures where total=0.0 or cumul=0.0;

delete from commandes where facture_id ='FAC_2020_0189-4720821'

-- Factures dont le cumul est incorrect
select f.no, f.total, f.cumul, sum(c.qty) AS Qty, sum(c.qty*p.price) AS TOT from factures f
join commandes c ON (f.no=c.facture_id)
join produits p ON (c.produit_id=p.name)
group by f.no
having abs(total-TOT)>0.01