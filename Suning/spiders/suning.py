# -*- coding: utf-8 -*-
import scrapy
import re
from copy import deepcopy


class SuningSpider(scrapy.Spider):
    name = 'suning'
    allowed_domains = ['suning.com']
    start_urls = ['https://book.suning.com/']

    def parse(self, response):
        # 现获取大分类的分组
        b_div_list = response.xpath("//div[@class='menu-list']/div[@class='menu-item']")
        # 中间分类的分组
        m_div_list = response.xpath("//div[@class='menu-sub']")
        for div in b_div_list:
            item = {}
            item["b_cate"] = div.xpath(".//h3/a/text()").extract_first()  # 大分类的名字
            index_now = b_div_list.index(div)  # 确定当前是第一个大分类
            now_menu_sub_div = m_div_list[index_now]  # 确定大分类对应的中间分类和小分类
            submenu_item_div = now_menu_sub_div.xpath(
                ".//div[@class='submenu-left']/p[@class='submenu-item']")  # 获取的是中间分类的分组
            for div in submenu_item_div:
                item["m_cate"] = div.xpath(".//a/text()").extract_first()  # 中间分类
                # following-sibling 选取当前节点之后的所有同级节点,即选取当前节点下的所有的li
                li_list = div.xpath("./following-sibling::ul[1]/li")  # 小分类的分组
                for li in li_list:
                    item["s_cate_href"] = li.xpath('./a/@href').extract_first()  # 小分类的url地址
                    item["s_cate"] = li.xpath('./a/text()').extract_first()  # 小分类的文本
                    # print(item)
                    yield scrapy.Request(  # 获取列表页的第一部分内容
                        item["s_cate_href"],
                        callback=self.parse_book_list,
                        meta={"item": deepcopy(item)}
                    )

                    # 获取列表页第一页的后一部分内容
                    next_part_url = "https://list.suning.com/emall/showProductList.do?ci={}&pg=03&cp=0&il=0&iy=0&adNumber=0&n=1&ch=4&sesab=ABBAAA&id=IDENTIFYING&cc=010&paging=1&sub=0"
                    ci = item["s_cate_href"].split("-")[1]
                    next_part_url = next_part_url.format(ci)
                    yield scrapy.Request(
                        next_part_url,
                        meta={"item": deepcopy(item)},
                        callback=self.parse_book_list
                    )

    def parse_book_list(self, response):
        item = response.meta["item"]
        # 首页请求获取前一部分的数据
        li_list = response.xpath("//div[@id='filter-results']//li[contains(@class,product)]")
        if len(li_list) == 0:  # 获取后一部分的数据
            li_list = response.xpath("//li[contains(@class,product)]")

        for li in li_list:
            item["book_title"] = li.xpath(".//p[@class='sell-point']/a/text()").extract_first().strip()
            item["book_href"] = li.xpath(".//p[@class='sell-point']/a/@href").extract_first().strip()
            yield response.follow(
                item["book_href"],
                callback=self.parse_book_detail,
                meta={"item": deepcopy(item)}
            )

        # TODO 翻页
        next_url_temp_1 = "https://list.suning.com/emall/showProductList.do?ci={}&pg=03&cp={}&il=0&iy=0&adNumber=0&n=1&ch=4&sesab=ABBAAA&id=IDENTIFYING&cc=010"
        next_url_temp_2 = "https://list.suning.com/emall/showProductList.do?ci={}&pg=03&cp={}&il=0&iy=0&adNumber=0&n=1&ch=4&sesab=ABBAAA&id=IDENTIFYING&cc=010&paging=1&sub=0"
        ci = item["s_cate_href"].split("-")[1]
        current_page = re.findall('param.currentPage = "(.*?)";', response.body.decode())[0]  # 提取当前页码数
        total_page = re.findall('param.pageNumbers = "(.*?)";', response.body.decode())[0]
        if int(current_page) < int(total_page):
            next_page_num = int(current_page) + 1
            next_url_1 = next_url_temp_1.format(ci, next_page_num)  # 数据的前一部分地址
            next_url_2 = next_url_temp_2.format(ci, next_page_num)  # 数据的前一部分地址
            # 构造前半部分数据的请求
            # print(">"*100)
            yield scrapy.Request(
                next_url_1,
                callback=self.parse_book_list,
                meta={"item": item}
            )
            # print("?"*100)
            # 构造后半部分数据的请求
            yield scrapy.Request(
                next_url_2,
                callback=self.parse_book_list,
                meta={"item": item}
            )

    def parse_book_detail(self, response):  # 获取详情页，提取字段组装价格的url地址
        item = response.meta["item"]
        price_url_temp = "https://pas.suning.com/nspcsale_0_000000000{}_000000000{}_{}_10_010_0100101_226503_1000000_9017_10106____{}_{}.html?callback=pcData&_=1526011028849"
        p1 = response.url.split("/")[-1].split(".")[0]
        p3 = response.url.split("/")[-2]
        # "catenIds":"R9011195",
        p4 = re.findall('"catenIds":"(.*?)",', response.body.decode())
        if len(p4) > 0:
            p4 = p4[0]
            # "weight":"0.5",
            p5 = re.findall('"weight":"(.*?)",', response.body.decode())[0]
            price_url = price_url_temp.format(p1, p1, p3, p4, p5)
            # print(price_url,"*"*100)
            yield scrapy.Request(
                price_url,
                callback=self.parse_book_price,
                meta={"item": item}
            )

    def parse_book_price(self, response):  # 获取价格
        item = response.meta["item"]
        item["book_price"] = re.findall('"netPrice":"(.*?)"', response.body.decode())[0]
        print(item)
